"""Coleta produtos da KaBuM! e grava no Oracle com SQLAlchemy.

Execute na raiz: python -m scraper.coletar URL --categoria SSD
Para ler HTML salvo: acrescente --html caminho/arquivo.html
O modo offline também grava no banco; use-o apenas com dados de teste.

Coleta em lote: python -m scraper.coletar --categorias GPU SSD RAM CPU
Use --max-paginas e --max-produtos para limitar cada categoria.
Acrescente --sem-gravar para validar o lote sem acessar o Oracle.
"""

import argparse
import json
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError

from scraper.banco import (
    PersistenciaError, criar_engine, listar_urls_para_rever, marcar_indisponivel, salvar_produto,
    registrar_resultado_coleta,
)
from scraper.categorias import CATEGORIAS, ColetorCategorias
from scraper.kabum import ColetaError, _url_produto, coletar_produto, extrair_produto
from scraper.modelos import PaginaRemovida
from scraper.execucao import ColetaEmAndamento, registrar_log_local, trava_coleta


def _registrar_resultado(engine, sucesso, categoria=None, url=None):
    codigo = None
    if url:
        try:
            codigo = _url_produto(url)
        except (ColetaError, ValueError, TypeError):
            pass
    try:
        with engine.begin() as conexao:
            registrar_resultado_coleta(conexao, sucesso, categoria, codigo)
        return True
    except (SQLAlchemyError, PersistenciaError):
        registrar_log_local("FALHA_BANCO")
        print("Não foi possível registrar o resultado no banco; consulte logs/coleta.log.", file=sys.stderr)
        return False


def _positivo(valor):
    numero = int(valor)
    if numero < 1:
        raise argparse.ArgumentTypeError("Informe um inteiro positivo.")
    return numero


def _coletar_categorias(args, diagnostico=None):
    engine = None
    resumo = {}
    try:
        if not args.sem_gravar:
            engine = criar_engine()
        coletor = ColetorCategorias()
        for categoria in dict.fromkeys(args.categorias):
            resultado = coletor.coletar(categoria, args.max_paginas, args.max_produtos)
            revisados = 0
            if engine is not None:
                try:
                    with engine.connect() as conexao:
                        codigos = [_url_produto(url) for url in resultado.verificados]
                        urls = listar_urls_para_rever(conexao, categoria, codigos, args.max_produtos)
                    revisao = coletor.rever(urls)
                    revisados = len(revisao.verificados)
                    resultado.produtos.extend(revisao.produtos)
                    resultado.removidos.extend(revisao.removidos)
                    resultado.falhas.extend(revisao.falhas)
                except (SQLAlchemyError, PersistenciaError):
                    resultado.falhas.append({"erro": "Falha ao consultar produtos cadastrados para revisão."})
            gravados = 0
            for produto in resultado.produtos:
                if engine is not None:
                    try:
                        with engine.begin() as conexao:
                            salvar_produto(conexao, produto, categoria)
                        gravados += 1
                    except (SQLAlchemyError, PersistenciaError):
                        resultado.falhas.append({"url": produto.url, "erro": "Falha ao gravar; transação desfeita."})
            indisponiveis = 0
            for removido in resultado.removidos:
                if engine is not None:
                    try:
                        with engine.begin() as conexao:
                            alteracao = marcar_indisponivel(conexao, removido["codigo_loja"])
                        indisponiveis += int(alteracao["acao"] == "indisponivel")
                    except (SQLAlchemyError, PersistenciaError):
                        resultado.falhas.append({"url": removido["url"], "erro": "Falha ao marcar indisponibilidade; transação desfeita."})
            if engine is not None:
                if resultado.falhas:
                    falha_log = False
                    for falha in list(resultado.falhas):
                        if not _registrar_resultado(engine, False, categoria, falha.get("url")):
                            falha_log = True
                    if falha_log:
                        resultado.falhas.append({"erro": "Falha ao registrar eventos no banco."})
                elif not _registrar_resultado(engine, True, categoria):
                    resultado.falhas.append({"erro": "Falha ao registrar resultado no banco."})
            resumo[categoria] = {
                "coletados": len(resultado.produtos), "gravados": gravados,
                "paginas": resultado.paginas, "limitado": resultado.limitado,
                "falhas": resultado.falhas,
                "removidos": len(resultado.removidos), "marcados_indisponiveis": indisponiveis,
                "revisados": revisados,
            }
        if engine is not None and len(resumo) > 1:
            # O status da loja deve refletir o lote inteiro, inclusive falhas em categorias anteriores.
            sucesso_lote = not any(item["falhas"] for item in resumo.values())
            if not _registrar_resultado(engine, sucesso_lote):
                resumo[categoria]["falhas"].append({"erro": "Falha ao registrar o resultado do lote."})
    except PersistenciaError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        registrar_log_local("FALHA_CONFIGURACAO")
        return 1
    except SQLAlchemyError:
        print("Falha ao preparar a conexão com o banco; confira a configuração local.", file=sys.stderr)
        registrar_log_local("FALHA_CONFIGURACAO")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    if diagnostico is not None:
        diagnostico(resumo)
    return int(any(item["falhas"] for item in resumo.values()))


def main(argv=None, *, diagnostico=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?")
    parser.add_argument("--categoria", choices=CATEGORIAS)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--categorias", nargs="+", choices=CATEGORIAS)
    parser.add_argument("--max-paginas", type=_positivo, default=1)
    parser.add_argument("--max-produtos", type=_positivo, default=20,
                        help="Máximo de produtos tentados por categoria, incluindo falhas")
    parser.add_argument("--sem-gravar", action="store_true", help="Validar coleta em lote sem acessar o banco")
    args = parser.parse_args(argv)
    try:
        with trava_coleta():
            return _executar(args, parser, diagnostico)
    except ColetaEmAndamento:
        print("Coleta ignorada: outra execução está em andamento.", file=sys.stderr)
        registrar_log_local("EXECUCAO_IGNORADA")
        return 2
    except OSError:
        print("Falha ao acessar a trava ou os arquivos locais da coleta.", file=sys.stderr)
        registrar_log_local("FALHA_EXECUCAO")
        return 1


def _executar(args, parser, diagnostico=None):
    if args.categorias:
        if args.url or args.categoria or args.html:
            parser.error("Use --categorias separadamente de URL, --categoria e --html.")
        return _coletar_categorias(args, diagnostico)
    if not args.url or not args.categoria or args.sem_gravar:
        parser.error("Informe URL e --categoria, ou use --categorias para coleta em lote.")
    engine = None
    try:
        engine = criar_engine()
        # A coleta termina antes de abrir a transação e bloquear a loja.
        try:
            produto = (extrair_produto(args.html.read_text(encoding="utf-8"), args.url)
                       if args.html else coletar_produto(args.url))
        except PaginaRemovida as erro:
            with engine.begin() as conexao:
                resultado = marcar_indisponivel(conexao, erro.codigo_loja)
            if not _registrar_resultado(engine, True, args.categoria, args.url):
                return 1
        else:
            with engine.begin() as conexao:
                resultado = salvar_produto(conexao, produto, args.categoria)
    except (ColetaError, PersistenciaError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        if engine is not None:
            _registrar_resultado(engine, False, args.categoria, args.url)
        else:
            registrar_log_local("FALHA_CONFIGURACAO")
        return 1
    except (SQLAlchemyError, OSError, UnicodeError):
        # Exceções do driver podem conter endereços, SQL e dados locais.
        print("Falha na coleta ou gravação; confira o arquivo de entrada, a conexão e o esquema. "
              "Dados da transação não foram confirmados.", file=sys.stderr)
        if engine is not None:
            _registrar_resultado(engine, False, args.categoria, args.url)
        else:
            registrar_log_local("FALHA_CONFIGURACAO")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
