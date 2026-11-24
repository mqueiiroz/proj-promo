"""Copia um snapshot do Oracle para o PostgreSQL local inicializado pela S5-2."""

from getpass import getpass

from sqlalchemy import MetaData, Table, URL, create_engine, select
from sqlalchemy.exc import SQLAlchemyError

from scraper.banco import criar_engine


TABELAS = ("loja", "produto", "historico_preco", "log_coleta", "usuario")


def migrar(origem, destino):
    with origem.connect() as oracle, destino.begin() as postgres:
        oracle.exec_driver_sql("SET TRANSACTION READ ONLY")
        postgres.exec_driver_sql("SET LOCAL TIME ZONE 'America/Manaus'")
        postgres.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
        postgres.exec_driver_sql(
            "LOCK TABLE public.loja, public.produto, public.historico_preco, "
            "public.log_coleta, public.usuario IN ACCESS EXCLUSIVE MODE"
        )
        metadata = MetaData()
        tabelas = {nome: Table(nome, metadata, schema="public", autoload_with=postgres) for nome in TABELAS}
        loja = tabelas["loja"]
        iniciais = postgres.execute(select(loja.c.id, loja.c.nome, loja.c.url_base,
                                           loja.c.ativa, loja.c.modelo_link_afiliado).order_by(loja.c.id)).all()
        if iniciais != [(1, "Kabum", "https://www.kabum.com.br", 1, None),
                        (2, "Terabyte", "https://www.terabyteshop.com.br", 1, None)]:
            raise ValueError("O destino não tem os cadastros iniciais esperados.")
        for nome in TABELAS[1:]:
            if postgres.execute(select(tabelas[nome].c.id).limit(1)).first() is not None:
                raise ValueError(f"A tabela {nome} já tem dados. Carga cancelada.")
        postgres.execute(loja.delete())
        contagens = {}
        metadata_oracle = MetaData()
        for nome, tabela in tabelas.items():
            original = Table(nome, metadata_oracle, autoload_with=oracle)
            colunas = [original.c[coluna.name] for coluna in tabela.columns]
            linhas = oracle.execute(select(*colunas).order_by(original.c.id)).mappings().all()
            for inicio in range(0, len(linhas), 500):
                lote = linhas[inicio:inicio + 500]
                postgres.execute(tabela.insert(), [dict(linha) for linha in lote])
            copiadas = postgres.execute(select(tabela).order_by(tabela.c.id)).mappings().all()
            if copiadas != linhas:
                raise ValueError(f"Os dados copiados de {nome} divergem do Oracle.")
            proximo_id = max(0, int(linhas[-1]["id"]) if linhas else 0) + 1
            postgres.exec_driver_sql(f"ALTER TABLE public.{nome} ALTER COLUMN id RESTART WITH {proximo_id}")
            contagens[nome] = len(linhas)
    return contagens


def main():
    origem = criar_engine()
    if origem.dialect.name != "oracle":
        raise ValueError("A conexão de origem deve apontar para o Oracle.")
    senha = getpass("Senha do PostgreSQL local (postgres): ")
    destino = create_engine(URL.create("postgresql+psycopg", username="postgres", password=senha,
                                      host="127.0.0.1", port=5432, database="proj_promo"),
                            hide_parameters=True)
    try:
        print("Linhas migradas e conferidas:", migrar(origem, destino))
    except SQLAlchemyError as erro:
        raise SystemExit(f"Carga não confirmada. Erro de banco: {type(erro).__name__}.") from None
    finally:
        origem.dispose()
        destino.dispose()


if __name__ == "__main__":
    main()
