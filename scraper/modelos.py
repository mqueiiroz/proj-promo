"""Contrato de dados compartilhado pelos coletores, independente do HTML das lojas."""

from dataclasses import dataclass, field
from decimal import Decimal


class ColetaError(ValueError):
    """A página não pôde ser coletada ou interpretada com segurança."""


class PaginaRemovida(ColetaError):
    """404/410 na própria URL de produto validada; não é uma falha transitória."""

    def __init__(self, url, codigo_loja, status):
        self.url = url
        self.codigo_loja = codigo_loja
        self.status = status
        super().__init__(f"Página do produto removida: HTTP {status}.")


@dataclass(frozen=True)
class Produto:
    codigo_loja: str
    nome: str
    preco: Decimal | None
    disponivel: bool
    url: str
    moeda: str = "BRL"
    imagem_url: str | None = None
    preco_original: Decimal | None = None


@dataclass
class ResultadoCategoria:
    produtos: list = field(default_factory=list)
    falhas: list = field(default_factory=list)
    paginas: int = 0
    limitado: bool = False
    removidos: list = field(default_factory=list)
    verificados: list = field(default_factory=list)
