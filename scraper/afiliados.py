"""Conversão local de URLs KaBuM! em deeplinks Awin, sem requisições HTTP.

ID 0 é apenas placeholder deste projeto, não um ID de teste oficial da Awin.
O funcionamento comercial depende de aprovação e do ID real do afiliado.
"""

import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

from dotenv import dotenv_values


ANUNCIANTE_KABUM = "17729"
ID_AFILIADO_TESTE = "0"


class AfiliadoError(ValueError):
    """Configuração ou URL incompatível com o conversor da KaBuM!."""


def _validar_id(valor):
    if not isinstance(valor, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,19})", valor):
        raise AfiliadoError("KABUM_AFILIADO_ID deve ser um inteiro não negativo, em texto, com até 20 dígitos.")
    return valor


def carregar_id_afiliado(env_path=None):
    """Usa variável do processo, depois .env, depois placeholder 0; não imprime dados."""
    caminho = Path(env_path) if env_path else Path(__file__).resolve().parents[1] / ".env"
    valores = dotenv_values(caminho)
    valor = os.environ.get("KABUM_AFILIADO_ID", valores.get("KABUM_AFILIADO_ID", ID_AFILIADO_TESTE))
    return _validar_id(valor)


def gerar_link_afiliado(url_original, id_afiliado=ID_AFILIADO_TESTE):
    """Função pura: preserva a URL original no parâmetro ued, codificada uma vez."""
    id_afiliado = _validar_id(id_afiliado)
    try:
        if (not isinstance(url_original, str) or len(url_original) > 1000
                or any(ord(c) <= 32 or ord(c) == 127 for c in url_original)):
            raise ValueError
        url = urlsplit(url_original)
        if (url.scheme != "https" or url.netloc != "www.kabum.com.br"
                or not re.fullmatch(r"/produto/[0-9]+(?:/[^/?#]+)?/?", url.path)
                or url.query or url.fragment):
            raise ValueError
    except (TypeError, ValueError):
        raise AfiliadoError("Informe uma URL HTTPS de produto da KaBuM!, sem parâmetros ou fragmento.") from None
    link = "https://www.awin1.com/cread.php?" + urlencode({
        "awinmid": ANUNCIANTE_KABUM, "awinaffid": id_afiliado, "ued": url_original,
    })
    if len(link) > 1500:
        raise AfiliadoError("Link de afiliado excede o limite de armazenamento.")
    return link
