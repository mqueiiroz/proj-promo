"""Conversão offline: nenhum teste abre links ou faz requisições à Awin."""

import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from scraper.afiliados import AfiliadoError, carregar_id_afiliado, gerar_link_afiliado


URL = "https://www.kabum.com.br/produto/621162/ssd-de-teste"


class AfiliadosTests(unittest.TestCase):
    def test_formato_awin_e_placeholder_padrao(self):
        partes = urlsplit(gerar_link_afiliado(URL))
        self.assertEqual(partes.scheme, "https")
        self.assertEqual(partes.netloc, "www.awin1.com")
        self.assertEqual(partes.path, "/cread.php")
        self.assertEqual(parse_qs(partes.query), {"awinmid": ["17729"], "awinaffid": ["0"], "ued": [URL]})

    def test_id_configuravel_e_destino_preservado_apos_uma_decodificacao(self):
        for url in [URL, URL + "-edição", URL + "-%C3%A7"]:
            with self.subTest(url=url):
                parametros = parse_qs(urlsplit(gerar_link_afiliado(url, "123456")).query)
                self.assertEqual(parametros["ued"], [url])
                self.assertEqual(parametros["awinaffid"], ["123456"])

    def test_ids_invalidos_nao_sao_incorporados_ao_link(self):
        for valor in [None, 123, "", "-1", "1&ued=outro", "TESTE", "01", "１２", "1" * 21]:
            with self.subTest(valor=valor), self.assertRaises(AfiliadoError):
                gerar_link_afiliado(URL, valor)

    def test_destinos_fora_do_escopo_e_links_ja_convertidos_sao_rejeitados(self):
        for url in [None, "javascript:alert(1)", URL.replace("https:", "http:"),
                    URL.replace("www.kabum.com.br", "example.com"),
                    URL.replace("www.kabum.com.br", "www.kabum.com.br.evil.example"),
                    URL.replace("www.kabum.com.br", "usuario@www.kabum.com.br"),
                    URL.replace("www.kabum.com.br", "www.kabum.com.br:8080"),
                    "https://www.kabum.com.br/login", URL + "?afiliado=123", URL + "#oferta",
                    URL + "\n", gerar_link_afiliado(URL)]:
            with self.subTest(url=url), self.assertRaises(AfiliadoError):
                gerar_link_afiliado(url)

    def test_limites_das_colunas_original_e_afiliado(self):
        for url in [URL + "a" * 1000, URL + "ç" * 300]:
            with self.assertRaises(AfiliadoError):
                gerar_link_afiliado(url)

    def test_configuracao_env_prioridade_default_e_valor_vazio(self):
        with patch("scraper.afiliados.dotenv_values", return_value={}) as arquivo, \
                patch.dict(os.environ, {}, clear=True):
            self.assertEqual(carregar_id_afiliado(), "0")
            arquivo.return_value = {"KABUM_AFILIADO_ID": "123"}
            self.assertEqual(carregar_id_afiliado(), "123")
            with patch.dict(os.environ, {"KABUM_AFILIADO_ID": "456"}):
                self.assertEqual(carregar_id_afiliado(), "456")
            arquivo.return_value = {"KABUM_AFILIADO_ID": ""}
            with self.assertRaises(AfiliadoError):
                carregar_id_afiliado()


if __name__ == "__main__":
    unittest.main()
