from datetime import date
from decimal import Decimal

import pytest

from desafio.erros import DadosInvalidosError
from desafio.formatacao import formatar_brl, ler_data, ler_valor
from desafio.juros import calcular_juros, dias_em_atraso

HOJE = date(2026, 10, 5)


@pytest.mark.parametrize(
    ("vencimento", "dias", "juros"),
    [
        (date(2026, 10, 20), 0, "0.00"),  # a vencer
        (HOJE, 0, "0.00"),  # vence hoje
        (date(2026, 10, 4), 1, "25.00"),
        (date(2026, 9, 25), 10, "250.00"),
        (date(2026, 1, 1), 277, "6925.00"),  # cruza meses
        (date(2025, 10, 5), 365, "9125.00"),  # um ano
    ],
)
def test_juros_simples_de_2_5_por_cento_ao_dia(vencimento, dias, juros):
    r = calcular_juros(Decimal("1000"), vencimento, HOJE)
    assert r.dias_em_atraso == dias
    assert r.juros == Decimal(juros)
    assert r.total == Decimal("1000") + Decimal(juros)


def test_arredondamento_em_centavos():
    # 33,33 x 2,5% x 3 = 2,49975 -> 2,50
    assert calcular_juros(Decimal("33.33"), date(2026, 10, 2), HOJE).juros == Decimal("2.50")


def test_virada_de_ano_e_bissexto():
    assert (
        dias_em_atraso(date(2023, 12, 31), date(2024, 3, 1)) == 61
    )  # 31 (jan) + 29 (fev, bissexto) + 1


def test_usa_data_de_hoje_por_padrao():
    assert calcular_juros(Decimal("100"), date.today()).dias_em_atraso == 0


def test_valor_negativo_rejeitado():
    with pytest.raises(DadosInvalidosError):
        calcular_juros(Decimal("-1"), HOJE, HOJE)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1000", "1000"),
        ("1000.50", "1000.50"),
        ("1000,50", "1000.50"),
        ("1.000,50", "1000.50"),
        ("1.500", "1500"),  # milhar brasileiro
        ("1.234.567,89", "1234567.89"),
        ("R$ 1.500,00", "1500.00"),
        ("  75  ", "75"),
    ],
)
def test_leitura_de_valores(texto, esperado):
    assert ler_valor(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", ["", "abc", "1,2,3", "NaN", "Infinity", "R$"])
def test_valor_ilegivel(texto):
    with pytest.raises(DadosInvalidosError):
        ler_valor(texto)


def test_leitura_de_datas():
    assert ler_data("05/10/2026") == HOJE
    assert ler_data("2026-10-05") == HOJE
    for ruim in ("31/02/2026", "2026/10/05", "hoje", ""):
        with pytest.raises(DadosInvalidosError):
            ler_data(ruim)


def test_formatar_brl():
    assert formatar_brl(Decimal("1234567.5")) == "R$ 1.234.567,50"
    assert formatar_brl(Decimal("0")) == "R$ 0,00"
