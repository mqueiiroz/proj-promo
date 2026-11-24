"""Paginação, limites e isolamento de falhas, sem acesso à loja ou ao Oracle."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from scraper.categorias import BASE, CATEGORIAS, ColetorCategorias, extrair_listagem
from scraper.coletar import main
from scraper.kabum import ColetaError, FalhaDns
from scraper.modelos import PaginaRemovida


FIXTURES = Path(__file__).parent / "fixtures"
HTML = (FIXTURES / "kabum_categoria.html").read_text(encoding="utf-8")
PRODUTO = (FIXTURES / "kabum_produto_completo.html").read_text(encoding="utf-8")


def listagem(codigos, pagina=1, total=1, categoria="GPU"):
    dados = {
        "slug": CATEGORIAS[categoria].lstrip("/"),
        "catalogServer": {
            "meta": {"page": {"number": pagina}, "totalPagesCount": total},
            "data": [{"code": c} for c in codigos],
        },
    }
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({
        "props": {"pageProps": {"data": json.dumps(dados)}},
    }) + '</script><a href="/produto/999">Recomendação fora do catálogo</a>'


def produto(codigo):
    return PRODUTO.replace("621162", str(codigo))


class ListagemTests(unittest.TestCase):
    def test_fixture_observada_e_urls_canonicas(self):
        urls, total = extrair_listagem(HTML, "GPU", 1)
        self.assertEqual(len(urls), 3)
        self.assertTrue(all(u.startswith(BASE + "/produto/") for u in urls))
        self.assertEqual(total, 8)

    def test_todas_as_categorias_sem_recomendacoes_ou_duplicados(self):
        for categoria in CATEGORIAS:
            with self.subTest(categoria=categoria):
                urls, _ = extrair_listagem(listagem([1, 1, 2], categoria=categoria), categoria, 1)
                self.assertEqual(urls, [BASE + "/produto/1", BASE + "/produto/2"])

    def test_bloqueio_html_alterado_categoria_e_pagina_erradas(self):
        for html in ["<html>Bloqueado</html>", listagem([]), listagem([1], pagina=2),
                     listagem([1], categoria="SSD"), listagem(["../login"]),
                     listagem([1], total=0)]:
            with self.subTest(html=html[:80]), self.assertRaises(ColetaError):
                extrair_listagem(html, "GPU", 1)


class ColetaCategoriasTests(unittest.TestCase):
    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_dns_transitorio_no_produto_recupera_sem_perder_resultado(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1]), FalhaDns(), produto(1)]
        resultado = ColetorCategorias().coletar("GPU")
        self.assertEqual([p.codigo_loja for p in resultado.produtos], ["1"])
        self.assertEqual(resultado.falhas, [])
        self.assertEqual(baixar.call_args_list[-2:], [baixar.call_args] * 2)

    @patch("scraper.categorias.time.monotonic", return_value=100)
    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_dns_persistente_pausa_requisicoes_e_volta_a_consultar_robots(self, baixar, dormir, relogio):
        baixar.side_effect = [FalhaDns(), FalhaDns(), "User-agent: *\nDisallow: /"]
        coletor = ColetorCategorias()
        self.assertTrue(coletor.coletar("GPU").falhas)
        self.assertTrue(coletor.coletar("SSD").falhas)
        self.assertEqual(baixar.call_count, 2)
        dormir.assert_called_once_with(5)
        relogio.return_value = 131
        resultado = coletor.coletar("GPU")
        self.assertEqual(baixar.call_count, 3)
        self.assertIn("robots.txt", resultado.falhas[0]["erro"])

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_produto_removido_nao_interrompe_demais_produtos(self, baixar, dormir):
        url = BASE + "/produto/1"
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1, 2]),
                              PaginaRemovida(url, "1", 410), produto(2)]
        r = ColetorCategorias().coletar("GPU")
        self.assertEqual([p.codigo_loja for p in r.produtos], ["2"])
        self.assertEqual(r.removidos, [{"url": url, "codigo_loja": "1", "http_status": 410}])
        self.assertEqual(r.falhas, [])

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_paginacao_cache_robots_e_deduplicacao(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nCrawl-delay: 3", listagem([1, 2], total=2),
                              produto(1), produto(2), listagem([2, 3], pagina=2, total=2), produto(3)]
        coletor = ColetorCategorias()
        r = coletor.coletar("GPU", max_paginas=3, max_produtos=10)
        self.assertEqual([p.codigo_loja for p in r.produtos], ["1", "2", "3"])
        self.assertEqual(r.paginas, 2)
        self.assertFalse(r.limitado)
        self.assertEqual(r.falhas, [])
        self.assertEqual(baixar.call_count, 6)
        self.assertEqual(baixar.call_args_list[4].args[0], BASE + CATEGORIAS["GPU"] + "?page_number=2")
        self.assertTrue(all(0 <= c.args[0] <= 3 for c in dormir.call_args_list))
        coletor.coletar("GPU", max_paginas=2, max_produtos=10)
        self.assertEqual(baixar.call_count, 6)  # cache durante a mesma execução

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_limite_de_produtos_conta_falhas_e_nao_acessa_paginas_extras(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1, 2, 3], total=2),
                              ColetaError("Falha de rede"), produto(2)]
        r = ColetorCategorias().coletar("GPU", max_paginas=2, max_produtos=2)
        self.assertEqual([p.codigo_loja for p in r.produtos], ["2"])
        self.assertEqual(len(r.falhas), 1)
        self.assertTrue(r.limitado)
        self.assertEqual(baixar.call_count, 4)

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_limite_de_paginas(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1], total=2), produto(1)]
        r = ColetorCategorias().coletar("GPU", max_paginas=1, max_produtos=10)
        self.assertTrue(r.limitado)
        self.assertEqual(r.paginas, 1)
        self.assertEqual(baixar.call_count, 3)

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_listagem_falha_preserva_resultados_anteriores(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1], total=2), produto(1), "Bloqueado"]
        r = ColetorCategorias().coletar("GPU", max_paginas=2)
        self.assertEqual(len(r.produtos), 1)
        self.assertEqual(len(r.falhas), 1)

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_paginacao_repetida_interrompe(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1], total=3), produto(1),
                              listagem([1], pagina=2, total=3)]
        r = ColetorCategorias().coletar("GPU", max_paginas=3)
        self.assertEqual(len(r.falhas), 1)
        self.assertEqual(baixar.call_count, 4)

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar", return_value="User-agent: *\nDisallow: /hardware/")
    def test_robots_bloqueia_categoria(self, baixar, dormir):
        r = ColetorCategorias().coletar("SSD")
        self.assertEqual(r.produtos, [])
        self.assertEqual(len(r.falhas), 1)
        baixar.assert_called_once_with(BASE + "/robots.txt")
        dormir.assert_not_called()

    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_robots_bloqueia_detalhes_do_produto(self, baixar, dormir):
        baixar.side_effect = ["User-agent: *\nDisallow: /produto/", listagem([1])]
        r = ColetorCategorias().coletar("GPU")
        self.assertEqual(r.produtos, [])
        self.assertEqual(len(r.falhas), 1)
        self.assertEqual(baixar.call_count, 2)

    def test_parametros_invalidos_falham_antes_da_rede(self):
        for categoria, paginas, produtos in [("HDD", 1, 1), ("GPU", 0, 1), ("GPU", 1, -1)]:
            with self.subTest(categoria=categoria, paginas=paginas, produtos=produtos):
                with self.assertRaises(ColetaError):
                    ColetorCategorias().coletar(categoria, paginas, produtos)


class ComandoCategoriasTests(unittest.TestCase):
    @patch("scraper.coletar.marcar_indisponivel")
    @patch("scraper.coletar.criar_engine")
    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_sem_gravar_nao_marca_removido_no_banco(self, baixar, dormir, engine, marcar):
        url = BASE + "/produto/1"
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1]), PaginaRemovida(url, "1", 404)]
        saida = StringIO()
        with redirect_stdout(saida):
            codigo = main(["--categorias", "GPU", "--sem-gravar"])
        resumo = json.loads(saida.getvalue())["GPU"]
        self.assertEqual(codigo, 0)
        self.assertEqual(resumo["removidos"], 1)
        self.assertEqual(resumo["marcados_indisponiveis"], 0)
        engine.assert_not_called()
        marcar.assert_not_called()

    @patch("scraper.coletar.registrar_resultado_coleta")
    @patch("scraper.coletar.listar_urls_para_rever", return_value=[])
    @patch("scraper.coletar.salvar_produto", side_effect=[SQLAlchemyError(), {"id": 2}])
    @patch("scraper.coletar.criar_engine")
    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_falha_de_gravacao_nao_impede_proximo_produto(self, baixar, dormir, engine, salvar, rever, registrar):
        baixar.side_effect = ["User-agent: *\nAllow: /", listagem([1, 2]), produto(1), produto(2)]
        saida = StringIO()
        with redirect_stdout(saida):
            codigo = main(["--categorias", "GPU"])
        resumo = json.loads(saida.getvalue())["GPU"]
        self.assertEqual(codigo, 1)
        self.assertEqual(resumo["coletados"], 2)
        self.assertEqual(resumo["gravados"], 1)
        self.assertEqual(len(resumo["falhas"]), 1)
        self.assertEqual(engine.return_value.begin.call_count, 3)  # dois produtos e log da falha
        registrar.assert_called_once()
        engine.return_value.dispose.assert_called_once()

    @patch("scraper.coletar.criar_engine")
    @patch("scraper.categorias.time.sleep")
    @patch("scraper.categorias._baixar")
    def test_sem_gravar_nao_abre_banco_e_continua_outra_categoria(self, baixar, dormir, engine):
        baixar.side_effect = ["User-agent: *\nAllow: /", "Bloqueado",
                              listagem([1], categoria="SSD"), produto(1)]
        saida = StringIO()
        with redirect_stdout(saida):
            codigo = main(["--categorias", "GPU", "SSD", "--sem-gravar"])
        resumo = json.loads(saida.getvalue())
        self.assertEqual(codigo, 1)
        self.assertEqual(resumo["GPU"]["coletados"], 0)
        self.assertEqual(resumo["SSD"]["coletados"], 1)
        self.assertEqual(resumo["SSD"]["gravados"], 0)
        engine.assert_not_called()

    def test_argumentos_ambiguos_e_limites_invalidos(self):
        for args in [["--categorias", "GPU", "--categoria", "SSD"],
                     ["--categorias", "GPU", "--max-paginas", "0"],
                     ["--categorias", "GPU", "--html", "arquivo.html"]]:
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as erro:
                main(args)
            self.assertEqual(erro.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
