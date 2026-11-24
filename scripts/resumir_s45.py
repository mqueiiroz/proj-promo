"""Registra os resultados da janela de validação a partir dos logs locais."""

from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from uuid import uuid4


LOGS = Path(__file__).resolve().parents[1] / "logs"
RESULTADOS = {"EXECUCAO_OK", "EXECUCAO_FALHA", "FALHA_EXECUCAO"}


def resumir(inicio, fim, pasta, *, correlacionar=False):
    contagens = [Counter() for _ in range(3)]
    falhas = []
    registro_mais_recente = None
    inicios = {}
    resultados = []
    for caminho in sorted(pasta.glob("coleta.log*")):
        if caminho.name not in {"coleta.log", "coleta.log.1", "coleta.log.2", "coleta.log.3"}:
            continue
        with caminho.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                try:
                    # Um registro legado foi gravado com uma vírgula avulsa no início.
                    entrada = json.loads(linha.lstrip().removeprefix(","))
                    data = datetime.fromisoformat(entrada["data"])
                    evento = entrada["evento"]
                except (KeyError, TypeError, ValueError):
                    continue
                if data.tzinfo is None:
                    continue
                execucao = entrada.get("execucao")
                if evento == "EXECUCAO_INICIADA" and isinstance(execucao, str):
                    inicios[execucao] = data
                if evento in RESULTADOS:
                    resultados.append((data, evento, execucao))
    for data, evento, execucao in resultados:
        referencia = inicios.get(execucao) if correlacionar and isinstance(execucao, str) else None
        if not correlacionar:
            referencia = data
        if referencia is None or not inicio <= referencia < fim:
            continue
        dia = (referencia - inicio) // timedelta(days=1)
        contagens[dia][evento] += 1
        if evento != "EXECUCAO_OK":
            falhas.append({"data": data.isoformat(), "evento": evento})
        if registro_mais_recente is None or data > registro_mais_recente:
            registro_mais_recente = data
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "disparos_previstos_por_dia": 96,
        "dias": [
            {
                "inicio": (inicio + timedelta(days=dia)).isoformat(),
                "sucessos": contagem["EXECUCAO_OK"],
                "falhas": contagem["EXECUCAO_FALHA"] + contagem["FALHA_EXECUCAO"],
            }
            for dia, contagem in enumerate(contagens)
        ],
        "falhas": sorted(falhas, key=lambda falha: falha["data"]),
        "ultimo_resultado": registro_mais_recente.isoformat() if registro_mais_recente else None,
    }


def main(inicio_texto, fim_texto, modo=None):
    inicio, fim = map(datetime.fromisoformat, (inicio_texto, fim_texto))
    if inicio.tzinfo is None or fim.tzinfo is None or fim - inicio != timedelta(days=3):
        raise ValueError("Informe uma janela de três dias com fuso horário.")
    if modo not in (None, "--revalidacao"):
        raise ValueError("Modo de resumo inválido.")
    revalidacao = modo is not None
    limite = fim + timedelta(minutes=30) if revalidacao else fim
    if datetime.now(fim.tzinfo) < limite:
        raise ValueError("A janela de validação ainda está em andamento.")
    dados = resumir(inicio, fim, LOGS, correlacionar=revalidacao)
    if revalidacao:
        for dia in dados["dias"]:
            dia["sem_resultado"] = max(0, 96 - dia["sucessos"] - dia["falhas"])
        dados["minimo_sucessos_por_dia"] = 92  # Pelo menos 95% dos 96 horários.
        dados["meta_de_sucessos_atingida"] = all(dia["sucessos"] >= 92 for dia in dados["dias"])
    destino = LOGS / ("s45-revalidacao.json" if revalidacao else "s45-resultado.json")
    temporario = destino.with_suffix(f".{uuid4().hex}.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporario.replace(destino)


if __name__ == "__main__":
    main(*sys.argv[1:])
