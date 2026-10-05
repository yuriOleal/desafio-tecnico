"""Exercício 3 - Juros por atraso.

A partir de um valor e de uma data de vencimento, calcula os juros até hoje
com taxa de 2,5% ao dia (juros simples sobre o valor original):

    juros = valor x 2,5% x dias em atraso

Vencimento hoje ou no futuro: sem atraso, portanto juros zero.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from desafio.erros import DadosInvalidosError

TAXA_DIARIA = Decimal("0.025")
CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class ResultadoJuros:
    valor: Decimal
    vencimento: date
    dias_em_atraso: int
    juros: Decimal

    @property
    def total(self) -> Decimal:
        return self.valor + self.juros


def dias_em_atraso(vencimento: date, hoje: date | None = None) -> int:
    hoje = hoje or date.today()
    return max((hoje - vencimento).days, 0)


def calcular_juros(valor: Decimal, vencimento: date, hoje: date | None = None) -> ResultadoJuros:
    """`hoje` é opcional e existe para tornar o cálculo determinístico em testes."""
    if valor < 0:
        raise DadosInvalidosError("O valor não pode ser negativo.")
    dias = dias_em_atraso(vencimento, hoje)
    juros = (valor * TAXA_DIARIA * dias).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return ResultadoJuros(valor=valor, vencimento=vencimento, dias_em_atraso=dias, juros=juros)
