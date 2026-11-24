"""Conexão e persistência. Não cria nem altera a estrutura do banco."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from dotenv import dotenv_values
from sqlalchemy import MetaData, Table, URL, create_engine, select

from scraper.categorias import CATEGORIAS
from scraper.modelos import Produto
from scraper.afiliados import AfiliadoError, carregar_id_afiliado, gerar_link_afiliado


class PersistenciaError(ValueError):
    """Configuração ou dados incompatíveis com a gravação."""


def criar_engine(env_path=None):
    """Lê o .env da raiz; variáveis do processo têm prioridade. Não imprime segredos."""
    caminho = Path(env_path) if env_path else Path(__file__).resolve().parents[1] / ".env"
    valores = {**dotenv_values(caminho), **os.environ}
    driver = valores.get("DB_DRIVER", "oracle")
    if driver not in {"oracle", "postgresql"}:
        raise PersistenciaError("DB_DRIVER deve ser oracle ou postgresql.")
    campo_banco = "DB_NAME" if driver == "postgresql" else "DB_SERVICE_NAME"
    campos = ("DB_HOST", "DB_PORT", campo_banco, "DB_USER", "DB_PASSWORD")
    if any(not valores.get(campo) for campo in campos):
        raise PersistenciaError("Configuração incompleta: confira as variáveis DB_* no .env.")
    try:
        porta = int(valores["DB_PORT"])
        if not 1 <= porta <= 65535:
            raise ValueError
    except ValueError:
        raise PersistenciaError("DB_PORT deve ser uma porta válida.") from None
    opcoes = dict(username=valores["DB_USER"], password=valores["DB_PASSWORD"],
                  host=valores["DB_HOST"], port=porta)
    if driver == "postgresql":
        sslmode = "prefer" if valores["DB_HOST"] == "127.0.0.1" else "require"
        url = URL.create("postgresql+psycopg", database=valores["DB_NAME"],
                         query={"sslmode": sslmode, "options": "-c timezone=America/Manaus"}, **opcoes)
    else:
        url = URL.create("oracle+oracledb", query={"service_name": valores["DB_SERVICE_NAME"]}, **opcoes)
    return create_engine(url, hide_parameters=True, pool_pre_ping=True)


def _agora(conexao):
    if conexao.dialect.name == "postgresql":
        # Preserva a hora de Manaus ao executar em servidores configurados em UTC.
        return datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None)
    return datetime.now()


def _bloquear_loja_kabum_ativa(conexao, metadata):
    loja = Table("loja", metadata, autoload_with=conexao)
    loja_id = conexao.execute(
        select(loja.c.id).where(loja.c.nome == "Kabum", loja.c.ativa == 1).with_for_update()
    ).scalar_one_or_none()
    if loja_id is None:
        raise PersistenciaError("Loja Kabum não cadastrada ou inativa.")
    return loja_id


def salvar_produto(conexao, produto: Produto, categoria: str):
    """Insere ou atualiza na transação do chamador, sem commit próprio.

    Bloqueia a linha da loja durante a transação para serializar gravações
    deste coletor e evitar duas inclusões simultâneas do mesmo produto.
    Imagem e preço original ausentes são preservados. O link de afiliado é
    gerado a partir da URL original e da configuração atual em cada gravação.
    Registra o primeiro preço coletado e as mudanças em relação ao último
    registro do histórico. Produto e histórico usam a mesma transação.
    Eventos de mudança são gravados na mesma transação em LOG_COLETA.
    """
    categoria = categoria.strip().upper()
    if categoria not in CATEGORIAS:
        raise PersistenciaError(f"Categoria inválida. Opções: {', '.join(CATEGORIAS)}.")
    try:
        url_afiliado = gerar_link_afiliado(produto.url, carregar_id_afiliado())
    except AfiliadoError as erro:
        raise PersistenciaError(str(erro)) from None
    metadata = MetaData()
    tabela = Table("produto", metadata, autoload_with=conexao)
    historico = Table("historico_preco", metadata, autoload_with=conexao)
    loja_id = _bloquear_loja_kabum_ativa(conexao, metadata)
    filtro = (tabela.c.loja_id == loja_id) & (tabela.c.codigo_loja == produto.codigo_loja)
    existente = conexao.execute(
        select(tabela.c.id, tabela.c.preco_atual, tabela.c.preco_original,
               tabela.c.disponivel, tabela.c.promocao_desde).where(filtro)
    ).mappings().one_or_none()
    agora = _agora(conexao)
    dados = dict(
        nome=produto.nome, categoria=categoria, url_original=produto.url, url_afiliado=url_afiliado,
        disponivel=int(produto.disponivel), visto_em=agora, atualizado_em=agora,
    )
    # Um item esgotado sem preço não deve apagar o último preço conhecido.
    if produto.preco is not None:
        dados["preco_atual"] = produto.preco
    if produto.imagem_url is not None:
        dados["imagem_url"] = produto.imagem_url
    if produto.preco_original is not None:
        dados["preco_original"] = produto.preco_original
    anteriores = existente if existente is not None else {}
    preco_atual = dados.get("preco_atual", anteriores.get("preco_atual"))
    preco_original = dados.get("preco_original", anteriores.get("preco_original"))
    promocao_desde = anteriores.get("promocao_desde")
    if not produto.disponivel or preco_atual is None or preco_original is None or preco_original <= preco_atual:
        dados["promocao_desde"] = None
    elif produto.preco is not None and (
        promocao_desde is None or preco_atual < anteriores["preco_atual"]
    ):
        dados["promocao_desde"] = agora
    if existente is None:
        conexao.execute(tabela.insert().values(
            loja_id=loja_id, codigo_loja=produto.codigo_loja, **dados,
        ))
        acao = "inserido"
    else:
        conexao.execute(tabela.update().where(filtro).values(**dados))
        acao = "atualizado"
    registro = conexao.execute(
        select(tabela.c.id, tabela.c.preco_original).where(filtro)
    ).mappings().one()
    produto_id = registro["id"]
    # Não cria observação de preço a partir de valor ausente ou de uma data passada.
    if produto.preco is not None:
        ultimo_preco = conexao.execute(
            select(historico.c.preco).where(historico.c.produto_id == produto_id)
            .order_by(historico.c.coletado_em.desc(), historico.c.id.desc()).limit(1)
        ).scalar_one_or_none()
        if ultimo_preco is None or ultimo_preco != produto.preco:
            conexao.execute(historico.insert().values(
                produto_id=produto_id, preco=produto.preco,
                preco_original=registro["preco_original"], coletado_em=agora,
            ))
    if existente is None:
        _registrar_evento(conexao, loja_id, "PRODUTO_NOVO", produto_id)
    else:
        if produto.preco is not None and existente["preco_atual"] is not None and produto.preco != existente["preco_atual"]:
            _registrar_evento(conexao, loja_id, "PRECO_ALTERADO", produto_id)
        if existente["disponivel"] in (0, 1) and existente["disponivel"] != int(produto.disponivel):
            _registrar_evento(conexao, loja_id, "VOLTOU_ESTOQUE" if produto.disponivel else "ESGOTADO", produto_id)
    _registrar_evento(conexao, loja_id, "COLETA_OK", produto_id, categoria)
    return {"id": int(produto_id), "acao": acao}


def marcar_indisponivel(conexao, codigo_loja: str):
    """Marca apenas produto KaBuM! existente, após remoção confirmada pelo coletor.

    Não cria produto nem observação de preço; preserva VISTO_EM, pois a página
    não foi encontrada. A transação é controlada pelo chamador.
    """
    if not isinstance(codigo_loja, str) or not codigo_loja.isascii() or not codigo_loja.isdigit():
        raise PersistenciaError("Código de produto inválido.")
    metadata = MetaData()
    tabela = Table("produto", metadata, autoload_with=conexao)
    loja_id = _bloquear_loja_kabum_ativa(conexao, metadata)
    filtro = (tabela.c.loja_id == loja_id) & (tabela.c.codigo_loja == codigo_loja)
    registro = conexao.execute(select(tabela.c.id, tabela.c.disponivel).where(filtro)).mappings().one_or_none()
    if registro is None:
        return {"id": None, "acao": "nao_cadastrado"}
    produto_id = registro["id"]
    conexao.execute(tabela.update().where(filtro).values(
        disponivel=0, promocao_desde=None, atualizado_em=_agora(conexao),
    ))
    if registro["disponivel"] == 1:
        _registrar_evento(conexao, loja_id, "ESGOTADO", produto_id)
    return {"id": int(produto_id), "acao": "indisponivel"}


def listar_urls_para_rever(conexao, categoria, codigos_excluidos, limite):
    """Seleciona URLs antigas para revisão limitada, sem mudar seus dados.

    Inclui indisponíveis para detectar volta ao estoque. Prioriza os produtos
    menos recentemente verificados; não há bloqueio durante acesso à loja.
    """
    if categoria not in CATEGORIAS or type(limite) is not int or limite < 1:
        raise PersistenciaError("Categoria ou limite inválido para revisão.")
    metadata = MetaData()
    loja = Table("loja", metadata, autoload_with=conexao)
    produto = Table("produto", metadata, autoload_with=conexao)
    consulta = select(produto.c.url_original).join(loja, loja.c.id == produto.c.loja_id).where(
        loja.c.nome == "Kabum", loja.c.ativa == 1, produto.c.categoria == categoria,
    )
    if codigos_excluidos:
        consulta = consulta.where(produto.c.codigo_loja.not_in(codigos_excluidos))
    consulta = consulta.order_by(produto.c.atualizado_em.asc().nulls_first(), produto.c.id.asc()).limit(limite)
    return list(conexao.execute(consulta).scalars())


def _registrar_evento(conexao, loja_id, tipo, produto_id=None, categoria=None):
    mensagens = {
        "PRODUTO_NOVO": "Produto cadastrado.", "PRECO_ALTERADO": "Preço atual alterado.",
        "ESGOTADO": "Produto marcado como indisponível.", "VOLTOU_ESTOQUE": "Disponibilidade restabelecida.",
        "COLETA_OK": "Coleta concluída sem falhas.", "COLETA_FALHA": "Coleta ou persistência apresentou falha; dados anteriores preservados nas operações não confirmadas.",
    }
    if tipo not in mensagens or categoria is not None and categoria not in CATEGORIAS:
        raise PersistenciaError("Tipo ou categoria de evento inválido.")
    mensagem = mensagens[tipo] + (f" Categoria: {categoria}." if categoria else "")
    log = Table("log_coleta", MetaData(), autoload_with=conexao)
    conexao.execute(log.insert().values(loja_id=loja_id, produto_id=produto_id, tipo=tipo,
                                      mensagem=mensagem, criado_em=_agora(conexao)))


def registrar_resultado_coleta(conexao, sucesso, categoria=None, codigo_loja=None):
    """Resultado em transação separada; só grava mensagens fixas, sem exceções."""
    metadata = MetaData()
    loja = Table("loja", metadata, autoload_with=conexao)
    loja_id = conexao.execute(select(loja.c.id).where(loja.c.nome == "Kabum")).scalar_one_or_none()
    if loja_id is None:
        raise PersistenciaError("Loja Kabum não cadastrada.")
    produto_id = None
    if codigo_loja is not None:
        produto = Table("produto", metadata, autoload_with=conexao)
        produto_id = conexao.execute(select(produto.c.id).where(
            produto.c.loja_id == loja_id, produto.c.codigo_loja == codigo_loja,
        )).scalar_one_or_none()
    _registrar_evento(conexao, loja_id, "COLETA_OK" if sucesso else "COLETA_FALHA", produto_id, categoria)
