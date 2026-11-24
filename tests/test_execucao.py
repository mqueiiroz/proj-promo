"""Trava local e entrada agendada, sem rede, Oracle ou registro de tarefa Windows."""

from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import ANY, MagicMock, call, patch
from uuid import uuid4
import subprocess
import sys

from sqlalchemy.exc import SQLAlchemyError

from scraper.agendado import main as agendado
from scraper.coletar import _registrar_resultado, main
from scraper.execucao import ColetaEmAndamento, _resumir_causas, trava_coleta
from scripts.resumir_s45 import resumir


class ExecucaoTests(unittest.TestCase):
    def setUp(self):
        # Arquivo direto evita as permissões especiais de TemporaryDirectory no Windows.
        self.caminho = Path(__file__).resolve().parents[1] / (".teste-" + uuid4().hex + ".lock")
        self.addCleanup(lambda: self.caminho.unlink(missing_ok=True))

    def test_duas_travas_concorrentes_e_liberacao(self):
        with trava_coleta(self.caminho):
            with self.assertRaises(ColetaEmAndamento):
                with trava_coleta(self.caminho):
                    self.fail("Segunda execução não deveria entrar")
        with trava_coleta(self.caminho):
            pass

    def test_excecao_libera_a_trava_sem_remover_o_arquivo(self):
        with self.assertRaises(RuntimeError):
            with trava_coleta(self.caminho):
                raise RuntimeError("Falha simulada")
        self.assertTrue(self.caminho.exists())
        with trava_coleta(self.caminho):
            pass

    def test_trava_tambem_bloqueia_outro_processo(self):
        codigo = (
            "import sys\nfrom scraper.execucao import trava_coleta, ColetaEmAndamento\n"
            "try:\n with trava_coleta(sys.argv[1]): pass\n"
            "except ColetaEmAndamento:\n sys.exit(2)\n"
        )
        with trava_coleta(self.caminho):
            resultado = subprocess.run([sys.executable, "-c", codigo, str(self.caminho)],
                                      cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(resultado.returncode, 2, resultado.stderr.decode(errors="replace"))

    @patch("scraper.coletar.registrar_log_local")
    @patch("scraper.coletar.criar_engine")
    @patch("scraper.coletar.trava_coleta", side_effect=ColetaEmAndamento())
    def test_execucao_concorrente_nao_abre_banco(self, trava, engine, log):
        with redirect_stderr(StringIO()):
            self.assertEqual(main(["--categorias", "SSD"]), 2)
        engine.assert_not_called()
        log.assert_called_once_with("EXECUCAO_IGNORADA")

    @patch("scraper.agendado.registrar_log_local")
    @patch("scraper.agendado.coletar", return_value=0)
    def test_entrada_agendada_usa_apenas_kabum_e_limites(self, coletar, log):
        self.assertEqual(agendado(), 0)
        self.assertEqual(coletar.call_args.args[0], ["--categorias", "GPU", "SSD", "RAM", "CPU",
                                                   "FONTE", "COOLER", "WATER_COOLER", "GABINETE", "HD", "PLACA_MAE",
                                                   "--max-paginas", "1", "--max-produtos", "20"])
        execucao = log.call_args_list[0].kwargs["execucao"]
        self.assertEqual(log.call_args_list, [call("EXECUCAO_INICIADA", execucao=execucao),
                                              call("EXECUCAO_OK", execucao=execucao)])

    @patch("scraper.agendado.registrar_log_local")
    @patch("scraper.agendado.coletar", side_effect=RuntimeError("senha-inventada"))
    def test_entrada_agendada_nao_registra_excecao_bruta(self, coletar, log):
        self.assertEqual(agendado(), 1)
        execucao = log.call_args_list[0].kwargs["execucao"]
        self.assertEqual(log.call_args_list, [call("EXECUCAO_INICIADA", execucao=execucao),
                                              call("FALHA_EXECUCAO", execucao=execucao)])

    @patch("scraper.agendado.registrar_log_local")
    @patch("scraper.agendado.coletar", return_value=2)
    def test_entrada_agendada_nao_duplica_execucao_ignorada(self, coletar, log):
        self.assertEqual(agendado(), 2)
        log.assert_called_once_with("EXECUCAO_INICIADA", execucao=ANY)

    def test_resumo_conta_resultado_apos_fim_pelo_inicio_da_execucao(self):
        inicio = datetime(2026, 11, 23, tzinfo=timezone.utc)
        fim = inicio + timedelta(days=3)
        registros = [
            (inicio - timedelta(minutes=1), "EXECUCAO_INICIADA", "anterior"),
            (inicio + timedelta(minutes=1), "EXECUCAO_OK", "anterior"),
            (fim - timedelta(minutes=1), "EXECUCAO_INICIADA", "janela"),
            (fim + timedelta(minutes=1), "EXECUCAO_OK", "janela"),
        ]
        pasta = MagicMock()
        caminho = MagicMock()
        caminho.name = "coleta.log"
        caminho.open.return_value = StringIO("\n".join(
            json.dumps({"data": data.isoformat(), "evento": evento, "execucao": execucao})
            for data, evento, execucao in registros
        ))
        pasta.glob.return_value = [caminho]
        dados = resumir(inicio, fim, pasta, correlacionar=True)
        self.assertEqual([dia["sucessos"] for dia in dados["dias"]], [0, 0, 1])

    def test_diagnostico_separa_http_rede_e_banco_sem_propagacao_de_detalhes(self):
        resumo = {"CPU": {"falhas": [
            {"url": "https://exemplo.invalid/privado", "erro": "Tempo de resposta da loja excedido."},
            {"erro": "A loja respondeu HTTP 503; coleta interrompida sem novas tentativas."},
            {"erro": "Falha ao gravar; transação desfeita."},
            {"erro": "senha-inventada"},
        ]}}
        self.assertEqual(_resumir_causas(resumo), {"CPU": {
            "TIMEOUT_LOJA": 1, "HTTP_503": 1, "GRAVACAO_PRODUTO": 1, "SEM_CLASSIFICACAO": 1,
        }})

    @patch("scraper.coletar.registrar_log_local")
    @patch("scraper.coletar.registrar_resultado_coleta", side_effect=SQLAlchemyError("senha-inventada"))
    def test_banco_indisponivel_usa_log_local_sem_excecao(self, registrar, log):
        from unittest.mock import MagicMock
        with redirect_stderr(StringIO()):
            self.assertFalse(_registrar_resultado(MagicMock(), False, "SSD"))
        log.assert_called_once_with("FALHA_BANCO")


if __name__ == "__main__":
    unittest.main()
