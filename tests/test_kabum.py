"""Validação offline do spike; nenhum teste acessa a loja ou o banco."""

from decimal import Decimal
from email.message import Message
from gzip import compress
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scraper.kabum import ColetaError, _baixar, coletar_produto, extrair_produto
from scraper.modelos import PaginaRemovida


URL = "https://www.kabum.com.br/produto/621162"
HTML = (Path(__file__).parent / "fixtures" / "kabum_produto.html").read_text(encoding="utf-8")


def pagina(preco="1149.99", disponibilidade="InStock", moeda="BRL"):
    oferta = {"priceCurrency": moeda, "availability": f"https://schema.org/{disponibilidade}"}
    if preco is not None:
        oferta["price"] = preco
    produto = {"@type": "Product", "sku": "621162", "name": "SSD de teste", "offers": oferta}
    return '<script type="application/ld+json">' + json.dumps(produto) + '</script>'


class KabumTests(unittest.TestCase):
    @patch("scraper.kabum.urlopen")
    def test_descompacta_resposta_gzip_antes_de_decodificar(self, abrir):
        resposta = BytesIO(compress(HTML.encode("utf-8")))
        resposta.url = URL
        resposta.headers = Message()
        resposta.headers["Content-Type"] = "text/html; charset=utf-8"
        resposta.headers["Content-Encoding"] = "gzip"
        abrir.return_value = resposta
        self.assertEqual(_baixar(URL), HTML)

    @patch("scraper.kabum.MAX_HTML_BYTES", 64)
    @patch("scraper.kabum.urlopen")
    def test_limita_gzip_descompactado_e_rejeita_resposta_truncada(self, abrir):
        for dados, mensagem in [
            (compress(b"a" * 1000), "Resposta maior"),
            (compress(b"<html>")[:-3], "Resposta comprimida inválida"),
        ]:
            with self.subTest(mensagem=mensagem):
                resposta = BytesIO(dados)
                resposta.url = URL
                resposta.headers = Message()
                resposta.headers["Content-Encoding"] = "gzip"
                abrir.return_value = resposta
                with self.assertRaisesRegex(ColetaError, mensagem):
                    _baixar(URL)

    @patch("scraper.kabum.urlopen")
    def test_404_e_410_na_url_do_produto_confirmam_remocao(self, abrir):
        for status in [404, 410]:
            abrir.side_effect = HTTPError(URL, status, "Removido", {}, None)
            with self.subTest(status=status), self.assertRaises(PaginaRemovida) as erro:
                _baixar(URL)
            self.assertEqual(erro.exception.codigo_loja, "621162")
            self.assertEqual(erro.exception.status, status)

    @patch("scraper.kabum.urlopen")
    def test_404_de_robots_categoria_ou_redirecionamento_nao_confirma_remocao(self, abrir):
        for solicitada, destino in [(URL, "https://www.kabum.com.br/login"),
                                    ("https://www.kabum.com.br/robots.txt", "https://www.kabum.com.br/robots.txt"),
                                    ("https://www.kabum.com.br/hardware/ssd-2-5", "https://www.kabum.com.br/hardware/ssd-2-5")]:
            abrir.side_effect = HTTPError(destino, 404, "Ausente", {}, None)
            with self.subTest(url=solicitada), self.assertRaises(ColetaError) as erro:
                _baixar(solicitada)
            self.assertNotIsInstance(erro.exception, PaginaRemovida)

    @patch("scraper.kabum.urlopen")
    def test_erros_de_acesso_nao_confirmam_remocao(self, abrir):
        for falha in [HTTPError(URL, 403, "Bloqueado", {}, None),
                      HTTPError(URL, 503, "Indisponível", {}, None),
                      TimeoutError(), URLError("Rede indisponível")]:
            abrir.side_effect = falha
            with self.subTest(tipo=type(falha).__name__), self.assertRaises(ColetaError) as erro:
                _baixar(URL)
            self.assertNotIsInstance(erro.exception, PaginaRemovida)

    def test_esgotado_com_preco_zero_nao_informa_queda_para_zero(self):
        self.assertIsNone(extrair_produto(pagina(preco="0", disponibilidade="OutOfStock"), URL).preco)

    def test_imagem_e_preco_original_observados(self):
        html = (Path(__file__).parent / "fixtures" / "kabum_produto_completo.html").read_text(encoding="utf-8")
        produto = extrair_produto(html, URL)
        self.assertEqual(produto.preco_original, Decimal("1529.40"))
        self.assertTrue(produto.imagem_url.startswith("https://images.kabum.com.br/"))
        with self.assertRaises(ColetaError):
            extrair_produto(html.replace('"id": 621162', '"id": 999'), URL)

    def test_campos_opcionais_ausentes_nao_sao_inventados(self):
        produto = extrair_produto(HTML, URL)
        self.assertIsNone(produto.preco_original)
        self.assertIsNone(produto.imagem_url)

    def test_campos_complementares_invalidos_geram_erro_de_coleta(self):
        html = (Path(__file__).parent / "fixtures" / "kabum_produto_completo.html").read_text(encoding="utf-8")
        for valor in [True, "NaN", -1, "12.345"]:
            with self.subTest(original=valor):
                partes = html.split('<script id="__NEXT_DATA__" type="application/json">')
                dados = json.loads(partes[1].split('</script>')[0])
                dados['props']['pageProps']['product']['prices']['oldPrice'] = valor
                alterado = partes[0] + '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(dados) + '</script>'
                with self.assertRaises(ColetaError):
                    extrair_produto(alterado, URL)
        with self.assertRaises(ColetaError):
            extrair_produto(pagina().replace('"name": "SSD de teste"',
                                            '"name": "SSD de teste", "image": "https://["'), URL)

    def test_produto_disponivel_com_preco_decimal(self):
        produto = extrair_produto(HTML, URL)
        self.assertEqual(produto.codigo_loja, "621162")
        self.assertIn("SSD Kingston NV3", produto.nome)
        self.assertEqual(produto.preco, Decimal("1149.99"))
        self.assertTrue(produto.disponivel)

    def test_esgotado_preserva_preco_quando_informado(self):
        produto = extrair_produto(pagina(disponibilidade="OutOfStock"), URL)
        self.assertFalse(produto.disponivel)
        self.assertEqual(produto.preco, Decimal("1149.99"))

    def test_esgotado_pode_nao_ter_preco(self):
        produto = extrair_produto(pagina(preco=None, disponibilidade="OutOfStock"), URL)
        self.assertFalse(produto.disponivel)
        self.assertIsNone(produto.preco)

    def test_disponivel_sem_preco_e_erro(self):
        with self.assertRaises(ColetaError):
            extrair_produto(pagina(preco=None), URL)

    def test_precos_invalidos_sao_rejeitados(self):
        for preco in ["NaN", "Infinity", "-1", "0", "12.345", "1.149,99", True]:
            with self.subTest(preco=preco), self.assertRaises(ColetaError):
                extrair_produto(pagina(preco=preco), URL)

    def test_disponibilidade_desconhecida_nao_vira_esgotado(self):
        with self.assertRaises(ColetaError):
            extrair_produto(pagina(disponibilidade="PreOrder"), URL)

    def test_outra_moeda_nao_e_tratada_como_reais(self):
        with self.assertRaises(ColetaError):
            extrair_produto(pagina(moeda="USD"), URL)

    def test_html_quebrado_ou_outro_produto_e_erro(self):
        for html in ["<html>Bloqueado</html>", '<script type="application/ld+json">{</script>',
                     HTML.replace('"621162"', '"999"'), HTML + HTML]:
            with self.subTest(html=html[:40]), self.assertRaises(ColetaError):
                extrair_produto(html, URL)

    def test_url_fora_do_escopo_e_rejeitada(self):
        for url in ["http://www.kabum.com.br/produto/621162", "https://example.com/produto/621162",
                    URL + "?query=teste", "https://www.kabum.com.br/login"]:
            with self.subTest(url=url), self.assertRaises(ColetaError):
                extrair_produto(HTML, url)

    @patch("scraper.kabum.time.sleep")
    @patch("scraper.kabum._baixar", side_effect=["User-agent: *\nDisallow: /produto/", HTML])
    def test_robots_impede_requisicao_ao_produto(self, baixar, dormir):
        with self.assertRaises(ColetaError):
            coletar_produto(URL)
        self.assertEqual(baixar.call_count, 1)
        dormir.assert_not_called()

    @patch("scraper.kabum.time.sleep")
    @patch("scraper.kabum._baixar", side_effect=["User-agent: *\nCrawl-delay: 5\n", HTML])
    def test_intervalo_e_coleta_de_uma_pagina(self, baixar, dormir):
        self.assertTrue(coletar_produto(URL).disponivel)
        dormir.assert_called_once_with(5)
        self.assertEqual(baixar.call_count, 2)


if __name__ == "__main__":
    unittest.main()
