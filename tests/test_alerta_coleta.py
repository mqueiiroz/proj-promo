from io import BytesIO
import json
from urllib.error import HTTPError

import pytest
from sqlalchemy.exc import SQLAlchemyError

from scraper import alerta_coleta, awin


@pytest.mark.parametrize(("funcao", "erro", "etapa"), [
    ("ler_feed", OSError("rede"), "Leitura do feed"),
    ("interpretar_feed", ValueError("CSV inválido"), "Validação do feed"),
    ("criar_engine", SQLAlchemyError("banco"), "Gravação no PostgreSQL"),
])
def test_falha_na_coleta_mantem_exit_code_e_notifica(monkeypatch, funcao, erro, etapa):
    avisos = []
    monkeypatch.setattr(awin, "ler_feed", lambda _: b"feed")
    monkeypatch.setattr(awin, "interpretar_feed", lambda _: ([], "123"))

    def falhar(*_):
        raise erro

    monkeypatch.setattr(awin, funcao, falhar)
    monkeypatch.setattr(awin, "enviar_alerta_coleta", avisos.append)
    assert awin.main([]) == 1
    assert avisos == [etapa]


def test_modo_sem_gravar_nao_envia_alerta(monkeypatch):
    def falhar(_):
        raise OSError("rede")

    monkeypatch.setattr(awin, "ler_feed", falhar)
    monkeypatch.setattr(awin, "enviar_alerta_coleta", lambda *_: pytest.fail("Envio inesperado"))
    assert awin.main(["--sem-gravar"]) == 1


def test_modo_de_teste_envia_alerta_sem_consultar_feed_ou_banco(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "chave-de-teste")
    monkeypatch.setenv("ALERTA_COLETA_DE", "radar@example.invalid")
    monkeypatch.setenv("ALERTA_COLETA_PARA", "admin@example.invalid")
    monkeypatch.setattr(awin, "ler_feed", lambda *_: pytest.fail("Consulta inesperada ao feed"))
    monkeypatch.setattr(awin, "criar_engine", lambda: pytest.fail("Acesso inesperado ao banco"))

    def enviar(requisicao, timeout):
        assert requisicao.full_url == "https://api.resend.com/emails"
        assert requisicao.get_method() == "POST"
        assert requisicao.get_header("Authorization") == "Bearer chave-de-teste"
        assert timeout == 10
        dados = json.loads(requisicao.data)
        assert dados["from"] == "radar@example.invalid"
        assert dados["to"] == ["admin@example.invalid"]
        assert dados["subject"].startswith("[Teste]")
        assert "Simulação de falha" in dados["text"]
        assert "Manaus" in dados["text"]
        return BytesIO(b'{"id":"envio-teste"}')

    monkeypatch.setattr(alerta_coleta, "urlopen", enviar)
    assert awin.main(["--testar-alerta"]) == 0


def test_erro_do_provedor_nao_expoe_detalhes(monkeypatch, capsys):
    monkeypatch.setenv("RESEND_API_KEY", "chave-de-teste")
    monkeypatch.setenv("ALERTA_COLETA_DE", "radar@example.invalid")
    monkeypatch.setenv("ALERTA_COLETA_PARA", "admin@example.invalid")

    def rejeitar(requisicao, timeout):
        raise HTTPError(requisicao.full_url, 403, "detalhes internos", None, None)

    monkeypatch.setattr(alerta_coleta, "urlopen", rejeitar)
    assert awin.main(["--testar-alerta"]) == 1
    assert capsys.readouterr().err.strip() == "Alerta não enviado: serviço de e-mail retornou HTTP 403."
