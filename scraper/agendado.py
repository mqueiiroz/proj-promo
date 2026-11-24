"""Entrada do Agendador Windows. Executar este módulo realiza coleta e gravação reais."""

from uuid import uuid4

from scraper.categorias import CATEGORIAS
from scraper.coletar import main as coletar
from scraper.execucao import registrar_log_local


def main(argv=None):
    execucao = uuid4().hex
    registrar_log_local("EXECUCAO_INICIADA", execucao=execucao)
    try:
        codigo = coletar(argv if argv is not None else [
            "--categorias", *CATEGORIAS, "--max-paginas", "1", "--max-produtos", "20",
        ], diagnostico=registrar_diagnostico)
    except Exception:
        # Nunca serializa exceções do driver, URLs ou configuração em arquivo.
        registrar_log_local("FALHA_EXECUCAO", execucao=execucao)
        return 1
    if codigo != 2:  # coletar já registra a contenção da trava.
        registrar_log_local("EXECUCAO_OK" if codigo == 0 else "EXECUCAO_FALHA", execucao=execucao)
    return codigo


def registrar_diagnostico(resumo):
    if any(categoria["falhas"] for categoria in resumo.values()):
        registrar_log_local("DIAGNOSTICO_COLETA", resumo=resumo)


if __name__ == "__main__":
    raise SystemExit(main())
