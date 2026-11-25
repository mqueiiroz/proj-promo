"""Importa o feed oficial KaBuM! da Awin para o PostgreSQL."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import gzip
from hashlib import sha256
import io
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

from sqlalchemy import MetaData, text
from sqlalchemy.exc import SQLAlchemyError

from scraper.afiliados import ANUNCIANTE_KABUM, gerar_link_afiliado
from scraper.banco import _bloquear_loja_kabum_ativa, _registrar_evento, criar_engine, salvar_produto
from scraper.modelos import Produto


CATEGORIAS_FEED = {
    ("hardware", "placa de vídeo (vga)"): "GPU",
    ("hardware", "ssd"): "SSD",
    ("hardware", "memória ram"): "RAM",
    ("hardware", "processadores"): "CPU",
    ("hardware", "fontes"): "FONTE",
    ("hardware", "coolers", "air cooler"): "COOLER",
    ("hardware", "coolers", "water cooler"): "WATER_COOLER",
    ("periféricos", "gabinetes"): "GABINETE",
    ("hardware", "disco rígido (hd)"): "HD",
    ("hardware", "placas-mãe"): "PLACA_MAE",
}
COLUNAS = {"merchant_product_id", "aw_product_id", "product_name", "merchant_category", "search_price",
           "currency", "in_stock", "merchant_deep_link", "aw_deep_link"}
MAX_BYTES = 64 * 1024 * 1024


def ler_feed(arquivo=None):
    if arquivo is None:
        url = os.environ.get("AWIN_FEED_URL", "")
        destino = urlsplit(url)
        if destino.scheme != "https" or destino.netloc != "productdata.awin.com":
            raise ValueError("Configure AWIN_FEED_URL com o link HTTPS de download da Awin.")
        try:
            with urlopen(url, timeout=45) as resposta:
                dados = resposta.read(MAX_BYTES + 1)
        except OSError as erro:
            status = getattr(erro, "code", None)
            raise ValueError(f"Falha ao baixar o feed (HTTP {status})." if status else
                             "Falha de conexão ao baixar o feed.") from None
    else:
        with arquivo.open("rb") as entrada:
            dados = entrada.read(MAX_BYTES + 1)
    if len(dados) > MAX_BYTES:
        raise ValueError("O feed ultrapassou o limite de tamanho.")
    if dados.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(dados)) as compactado:
            dados = compactado.read(MAX_BYTES + 1)
        if len(dados) > MAX_BYTES:
            raise ValueError("O CSV ultrapassou o limite após a descompactação.")
    return dados


def _preco(valor):
    if not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,2})?", valor):
        raise ValueError("Preço inválido no feed.")
    preco = Decimal(valor)
    if preco <= 0:
        raise ValueError("Preço inválido no feed.")
    return preco


def interpretar_feed(dados):
    leitor = csv.DictReader(io.StringIO(dados.decode("utf-8-sig"), newline=""))
    if not COLUNAS.issubset(leitor.fieldnames or ()):
        raise ValueError("O CSV não contém todas as colunas necessárias.")
    produtos = {}
    afiliados = set()
    for linha, registro in enumerate(leitor, start=2):
        try:
            caminho = tuple(parte.strip().casefold() for parte in registro["merchant_category"].split(">"))
            categoria = CATEGORIAS_FEED.get(caminho[:3]) or CATEGORIAS_FEED.get(caminho[:2])
            if categoria is None:
                continue
            codigo = registro["merchant_product_id"]
            url_loja = urlsplit(registro["merchant_deep_link"])
            if (not re.fullmatch(r"[0-9]{1,100}", codigo) or codigo in produtos or
                    url_loja.scheme != "https" or url_loja.netloc != "www.kabum.com.br" or
                    url_loja.path.split("/")[1:3] != ["produto", codigo] or
                    registro["currency"] != "BRL" or registro["in_stock"] not in {"0", "1"}):
                raise ValueError
            url = f"https://www.kabum.com.br/produto/{codigo}"
            link = urlsplit(registro["aw_deep_link"])
            parametros = parse_qs(link.query, keep_blank_values=True)
            afiliado, = parametros["a"]
            if (link.scheme != "https" or link.netloc != "www.awin1.com" or link.path != "/pclick.php"
                    or link.fragment or set(parametros) != {"a", "m", "p"}
                    or parametros["m"] != [ANUNCIANTE_KABUM] or parametros["p"] != [registro["aw_product_id"]]
                    or not re.fullmatch(r"[1-9][0-9]{0,19}", afiliado)):
                raise ValueError
            gerar_link_afiliado(url, afiliado)
            afiliados.add(afiliado)
            nome = registro["product_name"].strip()
            if not nome:
                raise ValueError
            imagem = registro.get("merchant_image_url") or None
            original = registro.get("product_price_old")
            disponivel = registro["in_stock"] == "1"
            preco = _preco(registro["search_price"]) if disponivel or registro["search_price"] else None
            produtos[codigo] = (categoria, Produto(
                codigo, nome[:300], preco, disponivel, url, imagem_url=imagem,
                preco_original=_preco(original) if original else None,
            ))
        except (AttributeError, KeyError, TypeError, ValueError, InvalidOperation):
            raise ValueError(f"Dados inválidos na linha {linha} do feed.") from None
    if not produtos or len(afiliados) != 1:
        raise ValueError("O feed precisa ter produtos das categorias atendidas e um único afiliado.")
    return produtos.values(), afiliados.pop()


def importar(engine, produtos, afiliado, versao):
    if engine.dialect.name != "postgresql":
        raise ValueError("A importação do feed requer DB_DRIVER=postgresql.")
    with engine.begin() as banco:
        metadata = MetaData()
        loja_id = _bloquear_loja_kabum_ativa(banco, metadata)
        banco.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS estado_feed_awin (
                loja_id BIGINT PRIMARY KEY REFERENCES loja (id), versao CHAR(64) NOT NULL
            )
        """)
        estado = {"loja_id": loja_id, "versao": versao}
        anterior = banco.execute(text("SELECT versao FROM estado_feed_awin WHERE loja_id = :loja_id"),
                                 {"loja_id": loja_id}).scalar_one_or_none()
        if anterior == versao:
            _registrar_evento(banco, loja_id, "COLETA_OK", metadata=metadata)
            return 0
        for categoria, produto in produtos:
            salvar_produto(banco, produto, categoria, metadata=metadata, loja_id=loja_id, id_afiliado=afiliado)
        banco.execute(text("""
            INSERT INTO estado_feed_awin (loja_id, versao) VALUES (:loja_id, :versao)
            ON CONFLICT (loja_id) DO UPDATE SET versao = EXCLUDED.versao
        """), estado)
        _registrar_evento(banco, loja_id, "COLETA_OK", metadata=metadata)
        return len(produtos)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, help="CSV local para validar a leitura")
    parser.add_argument("--sem-gravar", action="store_true")
    args = parser.parse_args(argv)
    engine = None
    try:
        dados = ler_feed(args.arquivo)
        produtos, afiliado = interpretar_feed(dados)
        if args.sem_gravar or args.arquivo is not None:
            print(f"Feed válido: {len(produtos)} produtos nas categorias atendidas; zero gravações.")
            return 0
        engine = criar_engine()
        total = importar(engine, produtos, afiliado, sha256(dados).hexdigest())
    except UnicodeError:
        print("Falha no feed: o arquivo precisa estar em UTF-8.", file=sys.stderr)
        return 1
    except ValueError as erro:
        print(f"Falha no feed: {erro}", file=sys.stderr)
        return 1
    except (SQLAlchemyError, OSError, EOFError, csv.Error):
        print("Falha ao ler o arquivo ou gravar o feed no PostgreSQL.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print(f"Feed importado: {total} produtos." if total else "Feed consultado: versão já processada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
