"""Isola os arquivos de execução dos testes da coleta agendada."""

import pytest

from scraper import execucao


@pytest.fixture(scope="session", autouse=True)
def isolar_arquivos_da_coleta(tmp_path_factory):
    with pytest.MonkeyPatch.context() as alterar:
        alterar.setattr(execucao, "RAIZ", tmp_path_factory.mktemp("execucao-testes"))
        yield
