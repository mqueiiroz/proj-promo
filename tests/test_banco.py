"""Testes isolados de persistência, sem acessar o Oracle local."""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import (Column, Integer, MetaData, Numeric, String, Table,
                        DateTime, ForeignKey, UniqueConstraint, create_engine, select)
from sqlalchemy.exc import IntegrityError

from scraper.banco import (PersistenciaError, listar_urls_para_rever, marcar_indisponivel,
                           registrar_resultado_coleta, salvar_produto)
from scraper.coletar import main
from scraper.kabum import Produto
from scraper.modelos import ColetaError, PaginaRemovida


class BancoTests(unittest.TestCase):
    def setUp(self):
        self.config_afiliado = patch("scraper.banco.carregar_id_afiliado", return_value="0")
        self.config_afiliado.start()
        self.addCleanup(self.config_afiliado.stop)
        self.engine = create_engine("sqlite://")
        metadata = MetaData()
        self.loja = Table("loja", metadata, Column("id", Integer, primary_key=True),
                          Column("nome", String), Column("ativa", Integer))
        self.produto = Table(
            "produto", metadata, Column("id", Integer, primary_key=True),
            Column("loja_id", Integer), Column("codigo_loja", String),
            Column("nome", String, nullable=False), Column("categoria", String),
            Column("url_original", String), Column("disponivel", Integer),
            Column("preco_atual", Numeric(10, 2)), Column("preco_original", Numeric(10, 2)),
            Column("url_afiliado", String), Column("imagem_url", String),
            Column("visto_em", DateTime), Column("atualizado_em", DateTime),
            Column("promocao_desde", DateTime),
            UniqueConstraint("loja_id", "codigo_loja"),
        )
        self.historico = Table(
            "historico_preco", metadata, Column("id", Integer, primary_key=True),
            Column("produto_id", Integer, ForeignKey("produto.id"), nullable=False),
            Column("preco", Numeric(10, 2), nullable=False),
            Column("preco_original", Numeric(10, 2)), Column("coletado_em", DateTime, nullable=False),
        )
        self.log = Table(
            "log_coleta", metadata, Column("id", Integer, primary_key=True),
            Column("loja_id", Integer, ForeignKey("loja.id"), nullable=False),
            Column("produto_id", Integer, ForeignKey("produto.id")),
            Column("tipo", String, nullable=False), Column("mensagem", String), Column("criado_em", DateTime),
        )
        metadata.create_all(self.engine)
        with self.engine.begin() as c:
            c.execute(self.loja.insert().values(nome="Kabum", ativa=1))
        self.item = Produto("621162", "SSD de teste", Decimal("100.00"), True,
                            "https://www.kabum.com.br/produto/621162")

    def tearDown(self):
        self.engine.dispose()

    def test_recoleta_atualiza_sem_duplicar(self):
        with self.engine.begin() as c:
            primeiro = salvar_produto(c, self.item, "SSD")
            segundo = salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            linhas = c.execute(select(self.produto)).mappings().all()
            self.assertEqual(primeiro["acao"], "inserido")
            self.assertEqual(segundo, {"id": primeiro["id"], "acao": "atualizado"})
            self.assertEqual(len(linhas), 1)
            self.assertEqual(linhas[0]["preco_atual"], Decimal("90.00"))
            self.assertIsNotNone(linhas[0]["visto_em"])

    def test_imagem_e_preco_original_gravados_e_preservados_quando_ausentes(self):
        with self.engine.begin() as c:
            salvar_produto(c, replace(self.item, imagem_url="https://images.kabum.com.br/ssd.jpg",
                                     preco_original=Decimal("150.00")), "SSD")
            salvar_produto(c, self.item, "SSD")
            linha = c.execute(select(self.produto)).mappings().one()
            self.assertEqual(linha["imagem_url"], "https://images.kabum.com.br/ssd.jpg")
            self.assertEqual(linha["preco_original"], Decimal("150.00"))

    def test_data_da_promocao_muda_na_queda_e_no_retorno_da_oferta(self):
        promocao = replace(self.item, preco_original=Decimal("150.00"))
        etapas = [
            (self.item, None),
            (promocao, 1),
            (promocao, 1),
            (replace(promocao, preco=Decimal("90.00")), 3),
            (replace(promocao, preco=Decimal("150.00")), None),
            (promocao, 5),
        ]
        with self.engine.begin() as c, patch("scraper.banco.datetime") as relogio:
            for minuto, (item, inicio) in enumerate(etapas):
                relogio.now.return_value = datetime(2026, 1, 1, 10, minuto)
                salvar_produto(c, item, "SSD")
                data = c.execute(select(self.produto.c.promocao_desde)).scalar_one()
                esperada = None if inicio is None else datetime(2026, 1, 1, 10, inicio)
                self.assertEqual(data, esperada)
            marcar_indisponivel(c, promocao.codigo_loja)
            self.assertIsNone(c.execute(select(self.produto.c.promocao_desde)).scalar_one())

    def test_esgotado_sem_preco_preserva_campos_existentes(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            c.execute(self.produto.update().values(preco_original=150, url_afiliado="link-teste"))
            salvar_produto(c, replace(self.item, preco=None, disponivel=False), "SSD")
            linha = c.execute(select(self.produto)).mappings().one()
            self.assertEqual(linha["preco_atual"], Decimal("100.00"))
            self.assertEqual(linha["preco_original"], Decimal("150.00"))
            self.assertEqual(parse_qs(urlsplit(linha["url_afiliado"]).query)["ued"], [self.item.url])
            self.assertEqual(linha["disponivel"], 0)

    def test_erro_posterior_desfaz_gravacao(self):
        with self.assertRaises(RuntimeError):
            with self.engine.begin() as c:
                salvar_produto(c, self.item, "SSD")
                raise RuntimeError("Falha simulada antes do commit")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto)).all(), [])
            self.assertEqual(c.execute(select(self.historico)).all(), [])
            self.assertEqual(c.execute(select(self.log)).all(), [])

    def test_eventos_de_transicao_sem_duplicar_recoletas_iguais(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00"), disponivel=False), "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00"), disponivel=False), "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            eventos = c.execute(select(self.log.c.tipo).where(
                self.log.c.tipo != "COLETA_OK",
            ).order_by(self.log.c.id)).scalars().all()
            self.assertEqual(eventos, ["PRODUTO_NOVO", "PRECO_ALTERADO", "ESGOTADO", "VOLTOU_ESTOQUE"])
            produto_id = c.execute(select(self.produto.c.id)).scalar_one()
            coletas = c.execute(select(self.log.c.produto_id).where(
                self.log.c.tipo == "COLETA_OK",
            )).scalars().all()
            self.assertEqual(coletas, [produto_id] * 6)

    def test_remocao_repetida_registra_esgotado_uma_vez(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            marcar_indisponivel(c, self.item.codigo_loja)
            marcar_indisponivel(c, self.item.codigo_loja)
            eventos = c.execute(select(self.log.c.tipo).order_by(self.log.c.id)).scalars().all()
            self.assertEqual(eventos, ["PRODUTO_NOVO", "COLETA_OK", "ESGOTADO"])

    def test_falha_do_log_desfaz_preco_e_historico(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            c.exec_driver_sql("CREATE TRIGGER rejeita_log BEFORE INSERT ON log_coleta "
                              "BEGIN SELECT RAISE(ABORT, 'Falha simulada'); END")
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as c:
                salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.preco_atual)).scalar_one(), Decimal("100.00"))
            self.assertEqual(c.execute(select(self.historico.c.preco)).scalars().all(), [Decimal("100.00")])

    def test_resultados_e_falha_sao_registrados_sem_mensagens_do_driver(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        with patch("scraper.coletar.criar_engine", return_value=self.engine), \
                patch.object(self.engine, "dispose"), \
                patch("scraper.coletar.coletar_produto", side_effect=ColetaError("segredo-que-nao-deve-ir-ao-log")), \
                redirect_stderr(StringIO()):
            self.assertEqual(main([self.item.url, "--categoria", "SSD"]), 1)
        with self.engine.begin() as c:
            registrar_resultado_coleta(c, True, "SSD")
            linhas = c.execute(select(self.log).order_by(self.log.c.id)).mappings().all()
            self.assertEqual([l["tipo"] for l in linhas], ["PRODUTO_NOVO", "COLETA_OK", "COLETA_FALHA", "COLETA_OK"])
            self.assertIsNotNone(linhas[1]["produto_id"])
            self.assertEqual(linhas[2]["produto_id"], linhas[1]["produto_id"])
            self.assertIsNone(linhas[3]["produto_id"])
            self.assertNotIn("segredo", str([l["mensagem"] for l in linhas]))

    def test_log_de_falha_persiste_apos_rollback_da_mutacao(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        with self.assertRaises(RuntimeError):
            with self.engine.begin() as c:
                salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
                raise RuntimeError("Falha simulada")
        with self.engine.begin() as c:
            registrar_resultado_coleta(c, False, "SSD", self.item.codigo_loja)
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.preco_atual)).scalar_one(), Decimal("100.00"))
            self.assertEqual(c.execute(select(self.log.c.tipo).order_by(self.log.c.id)).scalars().all(),
                             ["PRODUTO_NOVO", "COLETA_OK", "COLETA_FALHA"])

    def test_primeiro_preco_e_recoleta_igual_sem_duplicacao(self):
        with self.engine.begin() as c:
            resultado = salvar_produto(c, self.item, "SSD")
        # A deduplicação deve funcionar também entre execuções/transações.
        with self.engine.begin() as c:
            salvar_produto(c, replace(self.item, preco=Decimal("100.0")), "SSD")
            linhas = c.execute(select(self.historico)).mappings().all()
            self.assertEqual(len(linhas), 1)
            self.assertEqual(linhas[0]["produto_id"], resultado["id"])
            self.assertEqual(linhas[0]["preco"], Decimal("100.00"))
            self.assertIsNotNone(linhas[0]["coletado_em"])

    def test_queda_aumento_e_retorno_ao_preco_anterior(self):
        with self.engine.begin() as c:
            for preco in ["100.00", "90.00", "90.00", "110.00", "100.00"]:
                salvar_produto(c, replace(self.item, preco=Decimal(preco)), "SSD")
            precos = c.execute(select(self.historico.c.preco).order_by(self.historico.c.id)).scalars().all()
            self.assertEqual(precos, [Decimal(p) for p in ["100.00", "90.00", "110.00", "100.00"]])

    def test_produto_existente_sem_historico_inicia_na_proxima_observacao(self):
        with self.engine.begin() as c:
            # Simula um produto cadastrado antes da S2-3, sem inventar uma coleta passada.
            c.execute(self.produto.insert().values(
                loja_id=1, codigo_loja=self.item.codigo_loja, nome=self.item.nome,
                categoria="SSD", preco_atual=Decimal("100.00"), preco_original=Decimal("150.00"),
            ))
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, self.item, "SSD")
            linhas = c.execute(select(self.historico)).mappings().all()
            self.assertEqual(len(linhas), 1)
            self.assertEqual(linhas[0]["preco"], Decimal("100.00"))
            self.assertEqual(linhas[0]["preco_original"], Decimal("150.00"))

    def test_preco_original_isolado_nao_cria_ponto_e_mudanca_guarda_valor_vigente(self):
        with self.engine.begin() as c:
            salvar_produto(c, replace(self.item, preco_original=Decimal("150.00")), "SSD")
            salvar_produto(c, replace(self.item, preco_original=Decimal("140.00")), "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            linhas = c.execute(select(self.historico).order_by(self.historico.c.id)).mappings().all()
            self.assertEqual([(l["preco"], l["preco_original"]) for l in linhas],
                             [(Decimal("100.00"), Decimal("150.00")), (Decimal("90.00"), Decimal("140.00"))])

    def test_esgotado_sem_preco_nao_apaga_nem_duplica_historico(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, replace(self.item, preco=None, disponivel=False), "SSD")
            salvar_produto(c, replace(self.item, disponivel=False), "SSD")
            salvar_produto(c, self.item, "SSD")
            self.assertEqual(c.execute(select(self.historico.c.preco)).scalars().all(), [Decimal("100.00")])

    def test_primeiro_preco_apos_cadastro_sem_preco(self):
        with self.engine.begin() as c:
            salvar_produto(c, replace(self.item, preco=None, disponivel=False), "SSD")
            self.assertEqual(c.execute(select(self.historico)).all(), [])
            salvar_produto(c, self.item, "SSD")
            self.assertEqual(c.execute(select(self.historico.c.preco)).scalars().all(), [Decimal("100.00")])

    def test_precos_do_historico_sao_isolados_por_produto(self):
        with self.engine.begin() as c:
            a = salvar_produto(c, self.item, "SSD")
            b = salvar_produto(c, replace(self.item, codigo_loja="999", preco=Decimal("90.00")), "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            for produto_id, esperado in [(a["id"], [Decimal("100.00"), Decimal("90.00")]),
                                         (b["id"], [Decimal("90.00")])]:
                precos = c.execute(select(self.historico.c.preco).where(
                    self.historico.c.produto_id == produto_id).order_by(self.historico.c.id)).scalars().all()
                self.assertEqual(precos, esperado)

    def test_mesmo_instante_desempata_por_id_do_historico(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            instante = c.execute(select(self.historico.c.coletado_em).order_by(self.historico.c.id)).scalars().first()
            c.execute(self.historico.update().values(coletado_em=instante))
            salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
            self.assertEqual(len(c.execute(select(self.historico)).all()), 2)

    def test_falha_ao_inserir_historico_desfaz_atualizacao_do_produto(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            c.exec_driver_sql("CREATE TRIGGER falha_historico BEFORE INSERT ON historico_preco "
                              "BEGIN SELECT RAISE(ABORT, 'Falha simulada no historico'); END")
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as c:
                salvar_produto(c, replace(self.item, preco=Decimal("90.00")), "SSD")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.preco_atual)).scalar_one(), Decimal("100.00"))
            self.assertEqual(c.execute(select(self.historico.c.preco)).scalars().all(), [Decimal("100.00")])

    def test_loja_inativa_impede_gravacao(self):
        with self.engine.begin() as c:
            c.execute(self.loja.update().values(ativa=0))
            with self.assertRaises(PersistenciaError):
                salvar_produto(c, self.item, "SSD")
            self.assertEqual(c.execute(select(self.produto)).all(), [])

    def test_categoria_invalida_e_rejeitada(self):
        with self.engine.begin() as c:
            with self.assertRaises(PersistenciaError):
                salvar_produto(c, self.item, "OUTRA")

    def test_link_afiliado_gerado_e_renovado_sem_mudar_original_ou_historico(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            linha = c.execute(select(self.produto)).mappings().one()
            self.assertEqual(linha["url_original"], self.item.url)
            self.assertEqual(parse_qs(urlsplit(linha["url_afiliado"]).query)["awinaffid"], ["0"])
            with patch("scraper.banco.carregar_id_afiliado", return_value="123456"):
                salvar_produto(c, self.item, "SSD")
            linha = c.execute(select(self.produto)).mappings().one()
            self.assertEqual(linha["url_original"], self.item.url)
            self.assertEqual(parse_qs(urlsplit(linha["url_afiliado"]).query)["awinaffid"], ["123456"])
            self.assertEqual(len(c.execute(select(self.historico)).all()), 1)

    def test_url_ou_configuracao_afiliado_invalida_nao_altera_produto(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        for url, identificador in [("https://example.com/produto/621162", "0"), (self.item.url, "invalido")]:
            with self.assertRaises(PersistenciaError):
                with self.engine.begin() as c, patch("scraper.banco.carregar_id_afiliado", return_value=identificador):
                    salvar_produto(c, replace(self.item, url=url, preco=Decimal("90.00")), "SSD")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.preco_atual)).scalar_one(), Decimal("100.00"))
            self.assertEqual(len(c.execute(select(self.historico)).all()), 1)

    def test_remocao_preserva_dados_visto_em_e_historico_e_permite_retorno(self):
        with self.engine.begin() as c:
            salvar_produto(c, replace(self.item, preco_original=Decimal("150.00")), "SSD")
            antes = c.execute(select(self.produto)).mappings().one()
            marcar_indisponivel(c, self.item.codigo_loja)
            marcar_indisponivel(c, self.item.codigo_loja)
            depois = c.execute(select(self.produto)).mappings().one()
            self.assertEqual(depois["disponivel"], 0)
            for campo in ["nome", "preco_atual", "preco_original", "url_original", "visto_em"]:
                self.assertEqual(antes[campo], depois[campo])
            self.assertEqual(len(c.execute(select(self.historico)).all()), 1)
            salvar_produto(c, self.item, "SSD")
            self.assertEqual(c.execute(select(self.produto.c.disponivel)).scalar_one(), 1)
            self.assertEqual(len(c.execute(select(self.historico)).all()), 1)

    def test_remocao_de_codigo_desconhecido_nao_cria_produto(self):
        with self.engine.begin() as c:
            self.assertEqual(marcar_indisponivel(c, "999"), {"id": None, "acao": "nao_cadastrado"})
            self.assertEqual(c.execute(select(self.produto)).all(), [])
            self.assertEqual(c.execute(select(self.historico)).all(), [])

    def test_falha_posterior_desfaz_marcacao_de_indisponibilidade(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        with self.assertRaises(RuntimeError):
            with self.engine.begin() as c:
                marcar_indisponivel(c, self.item.codigo_loja)
                raise RuntimeError("Falha antes de confirmar")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.disponivel)).scalar_one(), 1)

    def test_selecao_para_revisao_respeita_categoria_limite_e_codigos_ja_verificados(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
            salvar_produto(c, replace(self.item, codigo_loja="999", url="https://www.kabum.com.br/produto/999"), "SSD")
            salvar_produto(c, replace(self.item, codigo_loja="888", url="https://www.kabum.com.br/produto/888"), "GPU")
            marcar_indisponivel(c, "999")
            urls = listar_urls_para_rever(c, "SSD", [self.item.codigo_loja], 1)
            self.assertEqual(urls, ["https://www.kabum.com.br/produto/999"])

    def test_comando_individual_removido_e_erros_transitorios(self):
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        for erro in [ColetaError("HTTP 403"), ColetaError("HTTP 503"), ColetaError("HTML inválido")]:
            with patch("scraper.coletar.criar_engine", return_value=self.engine), \
                    patch.object(self.engine, "dispose"), \
                    patch("scraper.coletar.coletar_produto", side_effect=erro), redirect_stderr(StringIO()):
                self.assertEqual(main([self.item.url, "--categoria", "SSD"]), 1)
            with self.engine.connect() as c:
                self.assertEqual(c.execute(select(self.produto.c.disponivel)).scalar_one(), 1)
        with patch("scraper.coletar.criar_engine", return_value=self.engine), \
                patch.object(self.engine, "dispose"), \
                patch("scraper.coletar.coletar_produto", side_effect=PaginaRemovida(self.item.url, self.item.codigo_loja, 404)), \
                redirect_stdout(StringIO()):
            self.assertEqual(main([self.item.url, "--categoria", "SSD"]), 0)
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(self.produto.c.disponivel)).scalar_one(), 0)
            self.assertEqual(len(c.execute(select(self.historico)).all()), 1)

    def test_coleta_limitada_confirma_remocao_de_url_antiga_sem_inferir_pela_ausencia(self):
        from pathlib import Path
        with self.engine.begin() as c:
            salvar_produto(c, self.item, "SSD")
        dados = {"slug": "hardware/ssd-2-5", "catalogServer": {
            "meta": {"page": {"number": 1}, "totalPagesCount": 2}, "data": [{"code": "999"}]}}
        lista = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(
            {"props": {"pageProps": {"data": json.dumps(dados)}}}) + '</script>'
        html = (Path(__file__).parent / "fixtures" / "kabum_produto_completo.html").read_text(encoding="utf-8").replace("621162", "999")
        for resposta, disponivel_esperado in [(ColetaError("HTTP 503"), 1),
                                             (PaginaRemovida(self.item.url, self.item.codigo_loja, 410), 0)]:
            saida = StringIO()
            with patch("scraper.coletar.criar_engine", return_value=self.engine), \
                    patch.object(self.engine, "dispose"), patch("scraper.categorias.time.sleep"), \
                    patch("scraper.categorias._baixar", side_effect=["User-agent: *\nAllow: /", lista, html, resposta]), \
                    redirect_stdout(saida):
                codigo = main(["--categorias", "SSD", "--max-produtos", "1"])
            resumo = json.loads(saida.getvalue())["SSD"]
            self.assertEqual(resumo["revisados"], 1)
            self.assertEqual(codigo, int(disponivel_esperado == 1))
            with self.engine.connect() as c:
                self.assertEqual(c.execute(select(self.produto.c.disponivel).where(
                    self.produto.c.codigo_loja == self.item.codigo_loja)).scalar_one(), disponivel_esperado)


if __name__ == "__main__":
    unittest.main()
