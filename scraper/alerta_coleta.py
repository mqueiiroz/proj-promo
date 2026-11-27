"""Envia avisos operacionais do coletor pela API HTTPS do Resend."""

from datetime import datetime, timedelta, timezone
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def enviar_alerta_coleta(etapa, *, teste=False):
    chave = os.environ.get("RESEND_API_KEY", "").strip()
    remetente = os.environ.get("ALERTA_COLETA_DE", "").strip()
    destinatario = os.environ.get("ALERTA_COLETA_PARA", "").strip()
    if not all((chave, remetente, destinatario)):
        print("Alerta não enviado: configure RESEND_API_KEY, ALERTA_COLETA_DE e ALERTA_COLETA_PARA.",
              file=sys.stderr)
        return False

    horario = datetime.now(timezone(timedelta(hours=-4))).strftime("%d/%m/%Y %H:%M:%S")
    assunto = "[Teste] Radar Hardware: falha na coleta" if teste else "Radar Hardware: falha na coleta"
    situacao = (
        "Falha simulada para testar o envio. Nenhum dado foi alterado."
        if teste else "O site continua exibindo os últimos dados gravados."
    )
    mensagem = {
        "from": remetente,
        "to": [destinatario],
        "subject": assunto,
        "text": f"Coleta da KaBuM! pela Awin\nEtapa: {etapa}\nHorário: {horario} (Manaus)\n\n{situacao}",
    }
    requisicao = Request("https://api.resend.com/emails", data=json.dumps(mensagem).encode("utf-8"), headers={
        "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
        "User-Agent": "RadarHardware-Coletor",
    })
    try:
        with urlopen(requisicao, timeout=10) as resposta:
            resultado = json.loads(resposta.read(8192))
        if isinstance(resultado, dict) and resultado.get("id"):
            print("Alerta aceito pelo serviço de e-mail.")
            return True
        print("Alerta não confirmado: resposta sem identificador de envio.", file=sys.stderr)
    except HTTPError as erro:
        print(f"Alerta não enviado: serviço de e-mail retornou HTTP {erro.code}.", file=sys.stderr)
    except (OSError, ValueError):
        print("Alerta não confirmado: falha na comunicação com o serviço de e-mail.", file=sys.stderr)
    return False
