"""Exercício 1 - Comissão por vendedor.

Regra aplicada a CADA venda (não ao total do vendedor):

    valor <  R$ 100,00              -> sem comissão
    R$ 100,00 <= valor < R$ 500,00  -> 1%
    valor >= R$ 500,00              -> 5%
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources
from pathlib import Path

from desafio.erros import DadosInvalidosError

CENTAVO = Decimal("0.01")

# (limite inferior inclusivo, taxa), do maior para o menor.
FAIXAS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("500.00"), Decimal("0.05")),
    (Decimal("100.00"), Decimal("0.01")),
)


@dataclass(frozen=True)
class Venda:
    vendedor: str
    valor: Decimal


@dataclass(frozen=True)
class ResumoVendedor:
    vendedor: str
    quantidade_vendas: int
    total_vendido: Decimal
    comissao: Decimal


def taxa_comissao(valor: Decimal) -> Decimal:
    """Taxa aplicável a uma venda de determinado valor."""
    for limite, taxa in FAIXAS:
        if valor >= limite:
            return taxa
    return Decimal("0")


def comissao_da_venda(valor: Decimal) -> Decimal:
    """Comissão de uma única venda (sem arredondar)."""
    return valor * taxa_comissao(valor)


def calcular_comissoes(vendas: Iterable[Venda]) -> list[ResumoVendedor]:
    """Agrupa por vendedor (na ordem de aparição) e soma vendas e comissões.

    O arredondamento para centavos é feito apenas no total de cada vendedor,
    para não acumular erro de arredondamento venda a venda.
    """
    total: dict[str, Decimal] = {}
    comissao: dict[str, Decimal] = {}
    quantidade: dict[str, int] = {}
    for venda in vendas:
        total[venda.vendedor] = total.get(venda.vendedor, Decimal("0")) + venda.valor
        comissao[venda.vendedor] = comissao.get(venda.vendedor, Decimal("0")) + comissao_da_venda(
            venda.valor
        )
        quantidade[venda.vendedor] = quantidade.get(venda.vendedor, 0) + 1

    return [
        ResumoVendedor(
            vendedor=nome,
            quantidade_vendas=quantidade[nome],
            total_vendido=total[nome].quantize(CENTAVO, rounding=ROUND_HALF_UP),
            comissao=comissao[nome].quantize(CENTAVO, rounding=ROUND_HALF_UP),
        )
        for nome in total
    ]


def parse_vendas(conteudo: str) -> list[Venda]:
    """Converte o JSON do desafio em objetos Venda, validando a estrutura."""
    try:
        # parse_float=Decimal evita passar por float e perder precisão.
        dados = json.loads(conteudo, parse_float=Decimal)
    except json.JSONDecodeError as erro:
        raise DadosInvalidosError(f"JSON inválido: {erro}.") from erro

    if not isinstance(dados, dict) or not isinstance(dados.get("vendas"), list):
        raise DadosInvalidosError("O JSON deve ter a chave 'vendas' com uma lista de vendas.")

    vendas = []
    for posicao, item in enumerate(dados["vendas"], start=1):
        if (
            not isinstance(item, dict)
            or isinstance(item.get("valor"), bool)
            or not isinstance(item.get("valor"), (int, Decimal))
        ):
            raise DadosInvalidosError(
                f"Venda #{posicao} inválida: esperado {{'vendedor': str, 'valor': número}}."
            )
        try:
            vendedor = item["vendedor"]
            valor = Decimal(item["valor"])
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise DadosInvalidosError(
                f"Venda #{posicao} inválida: esperado {{'vendedor': str, 'valor': número}}."
            ) from None
        if not isinstance(vendedor, str) or not vendedor.strip():
            raise DadosInvalidosError(f"Venda #{posicao}: nome do vendedor inválido.")
        if not valor.is_finite() or valor < 0:
            raise DadosInvalidosError(f"Venda #{posicao}: valor deve ser um número >= 0.")
        vendas.append(Venda(vendedor.strip(), valor))
    return vendas


def carregar_vendas(caminho: Path | None = None) -> list[Venda]:
    """Lê as vendas de um arquivo; sem caminho, usa o JSON do desafio empacotado."""
    try:
        if caminho is None:
            conteudo = resources.files("desafio").joinpath("dados/vendas.json").read_text("utf-8")
        else:
            conteudo = Path(caminho).read_text(encoding="utf-8")
    except OSError as erro:
        raise DadosInvalidosError(f"Não foi possível ler o arquivo de vendas: {erro}.") from erro
    return parse_vendas(conteudo)
