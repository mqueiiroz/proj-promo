"""Spike S1-4: coleta de um produto, sem persistência.

Uso online: python -m scraper.kabum https://www.kabum.com.br/produto/621162
Uso offline: python -m scraper.kabum https://www.kabum.com.br/produto/621162 --html arquivo.html

O preço é o informado na oferta estruturada da página (pode ser à vista).
Ele não inclui frete e não representa necessariamente o preço parcelado.
"""

import argparse
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from gzip import BadGzipFile, GzipFile
from html.parser import HTMLParser
from http.client import RemoteDisconnected
from io import BytesIO
import json
from pathlib import Path
import re
from socket import gaierror
from ssl import SSLError
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from zlib import error as ErroZlib

from scraper.modelos import ColetaError, PaginaRemovida, Produto


USER_AGENT = "MonitorPromocoesHardware/0.1 (academic local prototype)"
MAX_HTML_BYTES = 5_000_000
MENSAGEM_DNS = "Falha na resolução do endereço da loja."


class FalhaDns(ColetaError):
    def __init__(self):
        super().__init__(MENSAGEM_DNS)


class _DadosEstruturados(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.blocos = []
        self._partes = None
        self.proximo = None
        self._next_partes = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            if dict(attrs).get("id") == "__NEXT_DATA__":
                self._next_partes = []
            tipo = dict(attrs).get("type", "").split(";", 1)[0].strip().lower()
            if tipo == "application/ld+json":
                self._partes = []

    def handle_data(self, data):
        if self._next_partes is not None:
            self._next_partes.append(data)
        if self._partes is not None:
            self._partes.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._next_partes is not None:
            self.proximo = "".join(self._next_partes)
            self._next_partes = None
        if tag == "script" and self._partes is not None:
            self.blocos.append("".join(self._partes))
            self._partes = None


def _url_produto(url):
    partes = urlsplit(url)
    codigo = re.match(r"^/produto/(\d+)(?:/|$)", partes.path)
    if (partes.scheme != "https" or partes.netloc != "www.kabum.com.br"
            or not codigo or partes.query or partes.fragment):
        raise ColetaError("Use uma URL HTTPS de produto em www.kabum.com.br, sem parâmetros.")
    return codigo.group(1)


def _produtos_json(valor):
    if isinstance(valor, list):
        for item in valor:
            yield from _produtos_json(item)
    elif isinstance(valor, dict):
        tipos = valor.get("@type", [])
        if tipos == "Product" or isinstance(tipos, list) and "Product" in tipos:
            yield valor
        if "@graph" in valor:
            yield from _produtos_json(valor["@graph"])


def extrair_produto(html, url):
    """Extrai apenas o Product cujo SKU corresponde à URL; não acessa a rede."""
    codigo = _url_produto(url)
    parser = _DadosEstruturados()
    parser.feed(html)
    candidatos = []
    for bloco in parser.blocos:
        try:
            dados = json.loads(bloco, parse_float=Decimal)
        except (json.JSONDecodeError, InvalidOperation):
            continue
        candidatos.extend(p for p in _produtos_json(dados) if str(p.get("sku")) == codigo)
    if len(candidatos) != 1:
        raise ColetaError("Produto ausente ou ambíguo nos dados estruturados da página.")
    produto = candidatos[0]
    nome = produto.get("name")
    oferta = produto.get("offers")
    if not isinstance(nome, str) or not nome.strip() or not isinstance(oferta, dict):
        raise ColetaError("Nome ou oferta ausente nos dados do produto.")
    disponibilidade = oferta.get("availability")
    estados = {
        "https://schema.org/InStock": True,
        "http://schema.org/InStock": True,
        "https://schema.org/OutOfStock": False,
        "http://schema.org/OutOfStock": False,
        "https://schema.org/Discontinued": False,
        "http://schema.org/Discontinued": False,
    }
    if not isinstance(disponibilidade, str) or disponibilidade not in estados:
        raise ColetaError("Disponibilidade ausente ou não suportada; não é possível inferir estoque.")
    disponivel = estados[disponibilidade]
    if oferta.get("priceCurrency") != "BRL":
        raise ColetaError("Moeda ausente ou diferente de BRL.")
    valor = oferta.get("price")
    preco = None
    if valor is not None:
        try:
            if isinstance(valor, bool):
                raise InvalidOperation
            preco = Decimal(str(valor))
            if not preco.is_finite() or preco < 0 or (disponivel and preco == 0):
                raise InvalidOperation
            if preco != preco.quantize(Decimal("0.01")):
                raise InvalidOperation
            preco = preco.quantize(Decimal("0.01"))
            if not disponivel and preco == 0:
                preco = None  # zero em item esgotado não substitui o último preço conhecido
        except (InvalidOperation, ValueError):
            raise ColetaError("Preço inválido nos dados do produto.") from None
    elif disponivel:
        raise ColetaError("Produto disponível sem preço; coleta incompleta.")
    imagem = produto.get("image")
    if isinstance(imagem, list):
        imagem = imagem[0] if imagem else None
    if isinstance(imagem, dict):
        imagem = imagem.get("url")
    if imagem is not None:
        try:
            if (not isinstance(imagem, str) or len(imagem) > 1000
                    or urlsplit(imagem).scheme != "https" or not urlsplit(imagem).netloc):
                raise ValueError
        except ValueError:
            raise ColetaError("URL de imagem inválida.") from None
    original = None
    if parser.proximo:
        try:
            detalhes = json.loads(parser.proximo, parse_float=Decimal)["props"]["pageProps"]["product"]
            if str(detalhes["id"]) != codigo:
                raise ColetaError("Dados de preço original pertencem a outro produto.")
            valor_original = detalhes.get("prices", {}).get("oldPrice")
            if valor_original is not None:
                if isinstance(valor_original, bool):
                    raise InvalidOperation
                original = Decimal(str(valor_original))
                if (not original.is_finite() or original < 0
                        or original != original.quantize(Decimal("0.01"))):
                    raise InvalidOperation
                original = original.quantize(Decimal("0.01")) if original else None
        except (KeyError, TypeError, AttributeError, json.JSONDecodeError, InvalidOperation, ValueError):
            raise ColetaError("Dados complementares inválidos na página do produto.") from None
    return Produto(codigo, nome.strip(), preco, disponivel, url,
                   imagem_url=imagem, preco_original=original)


def _baixar(url):
    requisicao = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain"})
    try:
        with urlopen(requisicao, timeout=30) as resposta:
            if urlsplit(resposta.url).netloc != "www.kabum.com.br":
                raise ColetaError("Redirecionamento para fora da loja.")
            conteudo = resposta.read(MAX_HTML_BYTES + 1)
            if len(conteudo) > MAX_HTML_BYTES:
                raise ColetaError("Resposta maior que o limite da coleta experimental.")
            compressao = resposta.headers.get("Content-Encoding", "").strip().lower()
            if compressao == "gzip":
                with GzipFile(fileobj=BytesIO(conteudo)) as arquivo:
                    conteudo = arquivo.read(MAX_HTML_BYTES + 1)
                if len(conteudo) > MAX_HTML_BYTES:
                    raise ColetaError("Resposta maior que o limite da coleta experimental.")
            elif compressao not in {"", "identity"}:
                raise ColetaError("Compressão não suportada na resposta da loja.")
            return conteudo.decode(resposta.headers.get_content_charset() or "utf-8")
    except HTTPError as erro:
        status, destino = erro.code, erro.geturl()
        erro.close()
        if status in {404, 410} and destino == url:
            try:
                codigo = _url_produto(url)
            except ColetaError:
                pass  # 404 de categoria/robots não confirma remoção de produto.
            else:
                raise PaginaRemovida(url, codigo, status) from None
        raise ColetaError(f"A loja respondeu HTTP {status}; coleta interrompida sem novas tentativas.") from None
    except URLError as erro:
        if isinstance(erro.reason, gaierror):
            raise FalhaDns() from None
        raise ColetaError(_mensagem_rede(erro.reason)) from None
    except (BadGzipFile, EOFError, ErroZlib):
        raise ColetaError("Resposta comprimida inválida ou incompleta.") from None
    except (UnicodeError, LookupError):
        raise ColetaError("Codificação inválida na resposta da loja.") from None
    except gaierror:
        raise FalhaDns() from None
    except OSError as erro:
        raise ColetaError(_mensagem_rede(erro)) from None


def _mensagem_rede(erro):
    if isinstance(erro, TimeoutError):
        return "Tempo de resposta da loja excedido."
    if isinstance(erro, SSLError):
        return "Falha na conexão TLS com a loja."
    if isinstance(erro, RemoteDisconnected):
        return "A loja encerrou a conexão sem responder."
    if isinstance(erro, ConnectionResetError):
        return "A conexão com a loja foi interrompida."
    return "Falha ao acessar a loja; verifique a rede e tente novamente mais tarde."


def coletar_produto(url):
    """Consulta robots.txt, aguarda dois segundos e coleta uma única página."""
    _url_produto(url)
    partes = urlsplit(url)
    robots_url = urlunsplit((partes.scheme, partes.netloc, "/robots.txt", "", ""))
    robots = RobotFileParser()
    robots.parse(_baixar(robots_url).splitlines())
    if not robots.can_fetch(USER_AGENT, url):
        raise ColetaError("Coleta não permitida pelo robots.txt.")
    time.sleep(max(2, robots.crawl_delay(USER_AGENT) or 0))
    return extrair_produto(_baixar(url), url)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL pública de um produto da KaBuM!, sem parâmetros")
    parser.add_argument("--html", type=Path, help="Ler HTML salvo, sem requisições à loja")
    args = parser.parse_args(argv)
    try:
        produto = (extrair_produto(args.html.read_text(encoding="utf-8"), args.url)
                   if args.html else coletar_produto(args.url))
    except (ColetaError, OSError, UnicodeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    dados = asdict(produto)
    dados["preco"] = str(produto.preco) if produto.preco is not None else None
    dados["preco_original"] = str(produto.preco_original) if produto.preco_original is not None else None
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
