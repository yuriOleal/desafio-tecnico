from decimal import Decimal

import pytest

from desafio.comissoes import (
    calcular_comissoes,
    carregar_vendas,
    comissao_da_venda,
    parse_vendas,
    taxa_comissao,
)
from desafio.erros import DadosInvalidosError


@pytest.mark.parametrize(
    ("valor", "taxa"),
    [
        ("0.01", "0"),
        ("99.99", "0"),
        ("100.00", "0.01"),  # limite inferior é inclusivo
        ("499.99", "0.01"),
        ("500.00", "0.05"),  # limite inferior é inclusivo
        ("10000.00", "0.05"),
    ],
)
def test_faixas_de_comissao(valor, taxa):
    assert taxa_comissao(Decimal(valor)) == Decimal(taxa)


def test_comissao_da_venda():
    assert comissao_da_venda(Decimal("1000")) == Decimal("50")
    assert comissao_da_venda(Decimal("200")) == Decimal("2")
    assert comissao_da_venda(Decimal("50")) == Decimal("0")


def test_agrupa_por_vendedor_na_ordem_de_aparicao():
    vendas = parse_vendas(
        '{"vendas": ['
        '{"vendedor": "A", "valor": 1000.00}, {"vendedor": "B", "valor": 500.00},'
        '{"vendedor": "A", "valor": 200.00}, {"vendedor": "A", "valor": 50.00}]}'
    )
    resumo = calcular_comissoes(vendas)
    assert [r.vendedor for r in resumo] == ["A", "B"]
    a, b = resumo
    assert (a.quantidade_vendas, a.total_vendido, a.comissao) == (
        3,
        Decimal("1250.00"),
        Decimal("52.00"),
    )
    assert b.comissao == Decimal("25.00")


def test_arredonda_apenas_no_total():
    # 3 x (100,50 x 1%) = 3,015 -> 3,02 no total (arredondando por venda seria 3,03... ou 3,00)
    vendas = parse_vendas('{"vendas": [' + ",".join(['{"vendedor":"A","valor":100.50}'] * 3) + "]}")
    assert calcular_comissoes(vendas)[0].comissao == Decimal("3.02")


def test_resultado_do_json_do_desafio():
    """Valores conferidos manualmente com o JSON do enunciado."""
    resumo = {r.vendedor: r for r in calcular_comissoes(carregar_vendas())}
    esperado = {
        "João Silva": ("10754.70", "495.68"),
        "Maria Souza": ("9874.30", "465.95"),
        "Carlos Oliveira": ("7928.35", "379.37"),
        "Ana Lima": ("8763.95", "404.98"),
    }
    assert set(resumo) == set(esperado)
    for nome, (total, comissao) in esperado.items():
        assert resumo[nome].total_vendido == Decimal(total)
        assert resumo[nome].comissao == Decimal(comissao)


@pytest.mark.parametrize(
    "conteudo",
    [
        "isto não é json",
        "[]",
        '{"outra_chave": []}',
        '{"vendas": [{"vendedor": "A"}]}',
        '{"vendas": [{"vendedor": "", "valor": 10}]}',
        '{"vendas": [{"vendedor": "A", "valor": -5}]}',
        '{"vendas": [{"vendedor": "A", "valor": "abc"}]}',
        '{"vendas": [{"vendedor": "A", "valor": "100"}]}',
        '{"vendas": [{"vendedor": "A", "valor": true}]}',
        '{"vendas": [null]}',
        '{"vendas": [{"vendedor": 7, "valor": 10}]}',
    ],
)
def test_json_invalido_gera_erro_de_dominio(conteudo):
    with pytest.raises(DadosInvalidosError):
        parse_vendas(conteudo)


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(DadosInvalidosError):
        carregar_vendas(tmp_path / "nao_existe.json")
