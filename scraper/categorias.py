"""Descoberta paginada de produtos KaBuM! pelo catálogo incluído no HTML público."""

import json
import time
from urllib.robotparser import RobotFileParser

from scraper.kabum import (
    ColetaError, FalhaDns, USER_AGENT, _DadosEstruturados, _baixar, _url_produto, extrair_produto,
)
from scraper.modelos import PaginaRemovida, ResultadoCategoria


BASE = "https://www.kabum.com.br"
CATEGORIAS = {
    "GPU": "/hardware/placa-de-video-vga",
    "SSD": "/hardware/ssd-2-5",
    "RAM": "/hardware/memoria-ram",
    "CPU": "/hardware/processadores",
    "FONTE": "/hardware/fontes",
    "COOLER": "/hardware/coolers/air-cooler",
    "WATER_COOLER": "/hardware/coolers/water-cooler",
    "GABINETE": "/perifericos/gabinetes",
    "HD": "/hardware/disco-rigido-hd",
    "PLACA_MAE": "/hardware/placas-mae",
}


def extrair_listagem(html, categoria, pagina):
    """Retorna URLs canônicas e total de páginas; ignora recomendações e carrosséis."""
    parser = _DadosEstruturados()
    parser.feed(html)
    try:
        dados = json.loads(parser.proximo)["props"]["pageProps"]["data"]
        dados = json.loads(dados) if isinstance(dados, str) else dados
        if dados["slug"] != CATEGORIAS[categoria].lstrip("/"):
            raise ValueError
        catalogo = dados["catalogServer"]
        meta = catalogo["meta"]
        total = meta["totalPagesCount"]
        if (type(total) is not int or total < pagina
                or str(meta["page"]["number"]) != str(pagina)):
            raise ValueError
        itens = catalogo["data"]
        if not isinstance(itens, list) or not itens:
            raise ValueError
        urls = []
        for item in itens:
            codigo = str(item["code"])
            if not codigo.isascii() or not codigo.isdigit():
                raise ValueError
            url = f"{BASE}/produto/{codigo}"
            if url not in urls:
                urls.append(url)
        return urls, total
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ColetaError("Listagem ausente, inválida ou diferente da categoria/página solicitada.") from None


class ColetorCategorias:
    """Uma sessão por execução: robots, cache em memória e intervalo entre acessos.

    Nunca infere indisponibilidade por ausência na listagem ou por erro de rede.
    """

    def __init__(self):
        self._robots = None
        self._cache = {}
        self._ultimo_acesso = None
        self._dns_suspenso_ate = 0

    def _baixar_com_intervalo(self, url, intervalo):
        if self._ultimo_acesso is not None:
            time.sleep(max(0, intervalo - (time.monotonic() - self._ultimo_acesso)))
        try:
            return _baixar(url)
        finally:
            self._ultimo_acesso = time.monotonic()

    def _baixar_com_recuperacao(self, url, intervalo):
        if time.monotonic() < self._dns_suspenso_ate:
            raise FalhaDns()
        try:
            return self._baixar_com_intervalo(url, intervalo)
        except FalhaDns:
            try:
                return self._baixar_com_intervalo(url, max(5, intervalo))
            except FalhaDns:
                self._dns_suspenso_ate = time.monotonic() + 30
                raise

    def _ler(self, url):
        if url in self._cache:
            return self._cache[url]
        if self._robots is None:
            robots = RobotFileParser()
            robots.parse(self._baixar_com_recuperacao(f"{BASE}/robots.txt", 2).splitlines())
            self._robots = robots
        if not self._robots.can_fetch(USER_AGENT, url):
            raise ColetaError("Coleta não permitida pelo robots.txt.")
        intervalo = max(2, self._robots.crawl_delay(USER_AGENT) or 0)
        html = self._baixar_com_recuperacao(url, intervalo)
        self._cache[url] = html
        return html

    def coletar(self, categoria, max_paginas=1, max_produtos=20):
        if categoria not in CATEGORIAS:
            raise ColetaError(f"Categoria inválida. Opções: {', '.join(CATEGORIAS)}.")
        if (type(max_paginas) is not int or type(max_produtos) is not int
                or max_paginas < 1 or max_produtos < 1):
            raise ColetaError("Limites de páginas e produtos devem ser inteiros positivos.")
        resultado = ResultadoCategoria()
        vistos = set()
        total = 1
        for pagina in range(1, max_paginas + 1):
            url = BASE + CATEGORIAS[categoria]
            if pagina > 1:
                url += f"?page_number={pagina}"
            try:
                urls, total = extrair_listagem(self._ler(url), categoria, pagina)
            except ColetaError as erro:
                resultado.falhas.append({"url": url, "erro": str(erro)})
                break
            resultado.paginas += 1
            novos = [u for u in urls if u not in vistos]
            if not novos:
                resultado.falhas.append({"url": url, "erro": "Paginação repetiu apenas produtos já vistos."})
                break
            for indice, produto_url in enumerate(novos):
                vistos.add(produto_url)
                self._verificar(produto_url, resultado)
                if len(vistos) >= max_produtos:
                    resultado.limitado = indice < len(novos) - 1 or pagina < total
                    return resultado
            if pagina >= total:
                break
        resultado.limitado = resultado.paginas == max_paginas and max_paginas < total
        return resultado

    def _verificar(self, url, resultado):
        resultado.verificados.append(url)
        try:
            _url_produto(url)
            resultado.produtos.append(extrair_produto(self._ler(url), url))
        except PaginaRemovida as erro:
            resultado.removidos.append({"url": erro.url, "codigo_loja": erro.codigo_loja,
                                        "http_status": erro.status})
        except ColetaError as erro:
            resultado.falhas.append({"url": url, "erro": str(erro)})

    def rever(self, urls):
        """Revalida URLs já cadastradas; não interpreta ausência da listagem."""
        resultado = ResultadoCategoria()
        for url in dict.fromkeys(urls):
            self._verificar(url, resultado)
        return resultado
