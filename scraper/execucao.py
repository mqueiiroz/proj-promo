"""Trava entre processos e log local sanitizado para falhas de infraestrutura."""

from contextlib import contextmanager
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from logging import LogRecord, INFO
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re

from scraper.categorias import CATEGORIAS
from scraper.kabum import MENSAGEM_DNS
from scraper.log_janela import exportar_log_janela


RAIZ = Path(__file__).resolve().parents[1]


class ColetaEmAndamento(RuntimeError):
    pass


@contextmanager
def trava_coleta(caminho=None, *, aguardar=False):
    """O SO libera a trava ao encerrar o processo; o arquivo não é apagado."""
    arquivo = open(caminho or RAIZ / ".coleta.lock", "a+b")
    travado = False
    try:
        arquivo.seek(0, os.SEEK_END)
        if arquivo.tell() == 0:
            arquivo.write(b"0")
            arquivo.flush()
        arquivo.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_LOCK if aguardar else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX if aguardar else fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError, OSError) as erro:
            if erro.errno not in (11, 13, 36):
                raise
            raise ColetaEmAndamento("Já existe uma coleta em execução.") from None
        travado = True
        yield
    finally:
        if travado:
            arquivo.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
        arquivo.close()


def _resumir_causas(resumo):
    causas = {
        "Tempo de resposta da loja excedido.": "TIMEOUT_LOJA",
        MENSAGEM_DNS: "DNS_LOJA",
        "Falha na conexão TLS com a loja.": "TLS_LOJA",
        "A loja encerrou a conexão sem responder.": "LOJA_SEM_RESPOSTA",
        "A conexão com a loja foi interrompida.": "CONEXAO_INTERROMPIDA",
        "Falha ao acessar a loja; verifique a rede e tente novamente mais tarde.": "REDE_LOJA",
        "Coleta não permitida pelo robots.txt.": "ROBOTS_TXT",
        "Redirecionamento para fora da loja.": "REDIRECIONAMENTO_LOJA",
        "Resposta maior que o limite da coleta experimental.": "RESPOSTA_GRANDE",
        "Codificação inválida na resposta da loja.": "CODIFICACAO",
        "Compressão não suportada na resposta da loja.": "COMPRESSAO_NAO_SUPORTADA",
        "Resposta comprimida inválida ou incompleta.": "COMPRESSAO_INVALIDA",
        "Listagem ausente, inválida ou diferente da categoria/página solicitada.": "LISTAGEM_INVALIDA",
        "Paginação repetiu apenas produtos já vistos.": "PAGINACAO_REPETIDA",
        "Produto ausente ou ambíguo nos dados estruturados da página.": "PRODUTO_AUSENTE",
        "Nome ou oferta ausente nos dados do produto.": "OFERTA_AUSENTE",
        "Disponibilidade ausente ou não suportada; não é possível inferir estoque.": "ESTOQUE_INVALIDO",
        "Moeda ausente ou diferente de BRL.": "MOEDA_INVALIDA",
        "Preço inválido nos dados do produto.": "PRECO_INVALIDO",
        "Produto disponível sem preço; coleta incompleta.": "PRECO_AUSENTE",
        "URL de imagem inválida.": "IMAGEM_INVALIDA",
        "Dados complementares inválidos na página do produto.": "DADOS_COMPLEMENTARES_INVALIDOS",
        "Falha ao consultar produtos cadastrados para revisão.": "CONSULTA_BANCO",
        "Falha ao gravar; transação desfeita.": "GRAVACAO_PRODUTO",
        "Falha ao marcar indisponibilidade; transação desfeita.": "ATUALIZACAO_ESTOQUE",
        "Falha ao registrar eventos no banco.": "GRAVACAO_EVENTO",
        "Falha ao registrar resultado no banco.": "GRAVACAO_EVENTO",
        "Falha ao registrar o resultado do lote.": "GRAVACAO_EVENTO",
    }
    diagnostico = {}
    for categoria in CATEGORIAS:
        contagem = Counter()
        for falha in resumo.get(categoria, {}).get("falhas", []):
            mensagem = falha.get("erro", "")
            http = re.fullmatch(r"A loja respondeu HTTP ([45][0-9]{2}); coleta interrompida sem novas tentativas\.", mensagem)
            codigo = f"HTTP_{http[1]}" if http else causas.get(mensagem, "SEM_CLASSIFICACAO")
            contagem[codigo] += 1
        if contagem:
            diagnostico[categoria] = dict(contagem)
    return diagnostico


def registrar_log_local(evento, *, resumo=None, execucao=None):
    """Aceita somente códigos fixos; nunca recebe exceção, URL, SQL ou credencial."""
    mensagens = {
        "FALHA_BANCO": "Não foi possível registrar o resultado no banco.",
        "FALHA_CONFIGURACAO": "Configuração ou conexão indisponível.",
        "FALHA_EXECUCAO": "Execução interrompida por falha inesperada.",
        "EXECUCAO_OK": "Execução concluída sem falhas.",
        "EXECUCAO_INICIADA": "Entrada agendada iniciada.",
        "EXECUCAO_FALHA": "Execução terminou com falhas; consulte o resumo e LOG_COLETA.",
        "EXECUCAO_IGNORADA": "Outra coleta está em andamento; execução ignorada.",
        "DIAGNOSTICO_COLETA": "Contagem de falhas por categoria e causa.",
    }
    if evento not in mensagens:
        raise ValueError("Evento local inválido.")
    try:
        pasta = RAIZ / "logs"
        pasta.mkdir(exist_ok=True)
        with trava_coleta(pasta / "coleta-log.lock", aguardar=True):
            handler = RotatingFileHandler(pasta / "coleta.log", maxBytes=1_048_576, backupCount=3, encoding="utf-8")
            try:
                registro = {
                    "data": datetime.now(timezone(timedelta(hours=-4))).isoformat(),
                    "evento": evento, "mensagem": mensagens[evento],
                }
                if evento == "DIAGNOSTICO_COLETA":
                    registro["causas"] = _resumir_causas(resumo or {})
                if execucao is not None and re.fullmatch(r"[0-9a-f]{32}", execucao):
                    registro["execucao"] = execucao
                conteudo = json.dumps(registro, ensure_ascii=False)
                handler.handleError = lambda record: None
                handler.emit(LogRecord("coleta", INFO, "", 0, conteudo, (), None))
            finally:
                handler.close()
            exportar_log_janela(pasta, agora=datetime.fromisoformat(registro["data"]))
    except (OSError, ColetaEmAndamento):
        pass  # Não mascara a falha original caso o disco também esteja indisponível.
