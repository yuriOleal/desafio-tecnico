"""Formatação e leitura de valores no padrão brasileiro."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from desafio.erros import DadosInvalidosError

_MILHAR_BR = re.compile(r"^\d{1,3}(\.\d{3})+$")


def formatar_brl(valor: Decimal) -> str:
    """Decimal('1234.5') -> 'R$ 1.234,50'."""
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def ler_valor(texto: str) -> Decimal:
    """Lê valores monetários em vários formatos.

    Aceita '1500', '1500.50', '1500,50', '1.500,50', '1.500' (milhar) e 'R$ 1.500,50'.
    """
    limpo = texto.strip().upper().replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif _MILHAR_BR.match(limpo):
        limpo = limpo.replace(".", "")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise DadosInvalidosError(f"Valor inválido: {texto!r}.") from None
    if not valor.is_finite():
        raise DadosInvalidosError(f"Valor inválido: {texto!r}.")
    return valor


def ler_data(texto: str) -> date:
    """Lê datas em dd/mm/aaaa (padrão BR) ou aaaa-mm-dd (ISO)."""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            continue
    raise DadosInvalidosError(f"Data inválida: {texto!r}. Use dd/mm/aaaa.")
