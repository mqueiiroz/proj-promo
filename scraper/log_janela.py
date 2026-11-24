"""Mantém uma cópia JSONL dos eventos da janela de revalidação S4-5."""

from datetime import datetime, timedelta
import json


def exportar_log_janela(pasta, *, agora=None):
    try:
        janela = json.loads((pasta / "s45-janela-revalidacao.json").read_text(encoding="utf-8-sig"))
        inicio = datetime.fromisoformat(janela["Inicio"])
        fim = datetime.fromisoformat(janela["Fim"])
        if inicio.tzinfo is None or fim.tzinfo is None or inicio >= fim:
            return
        if agora is not None and not inicio <= agora <= fim + timedelta(minutes=30):
            return
    except (OSError, ValueError, TypeError, KeyError):
        return

    linhas = []
    execucoes = set()
    for nome in ("coleta.log.3", "coleta.log.2", "coleta.log.1", "coleta.log"):
        caminho = pasta / nome
        if not caminho.is_file():
            continue
        with caminho.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip().removeprefix(",").lstrip()
                try:
                    registro = json.loads(linha)
                    data = datetime.fromisoformat(registro["data"])
                except (KeyError, TypeError, ValueError):
                    continue
                if data.tzinfo is None:
                    continue
                execucao = registro.get("execucao")
                if inicio <= data < fim:
                    if registro.get("evento") == "EXECUCAO_INICIADA" and isinstance(execucao, str):
                        execucoes.add(execucao)
                    linhas.append(linha + "\n")
                elif fim <= data <= fim + timedelta(minutes=30) and isinstance(execucao, str) and execucao in execucoes:
                    linhas.append(linha + "\n")

    temporario = pasta / "coleta-s45-revalidacao.tmp"
    temporario.write_text("".join(linhas), encoding="utf-8")
    temporario.replace(pasta / "coleta-s45-revalidacao.log")
