import json

import pytest

from desafio.erros import DadosInvalidosError, EstoqueError
from desafio.estoque import Estoque, TipoMovimentacao, diretorio_dados


@pytest.fixture
def estoque():
    return Estoque.abrir()


def test_primeira_execucao_cria_estoque_a_partir_do_json_do_desafio(estoque):
    assert [(p.codigo, p.quantidade) for p in estoque.produtos()] == [
        (101, 150),
        (102, 75),
        (103, 200),
        (104, 320),
        (105, 90),
    ]
    assert (diretorio_dados() / "estoque.json").exists()


def test_entrada_soma_e_retorna_quantidade_final(estoque):
    m = estoque.movimentar(101, TipoMovimentacao.ENTRADA, 50, "Compra")
    assert m.quantidade_final == 200
    assert estoque.buscar_produto(101).quantidade == 200


def test_saida_subtrai_e_retorna_quantidade_final(estoque):
    m = estoque.movimentar(102, "saida", 25, "Venda")
    assert m.quantidade_final == 50 and m.tipo is TipoMovimentacao.SAIDA


def test_aceita_tipo_com_acento(estoque):
    assert estoque.movimentar(101, "SAÍDA", 1, "Venda").quantidade_final == 149


def test_ids_unicos_e_sequenciais(estoque):
    ids = [estoque.movimentar(101, "entrada", 1, "Compra").id for _ in range(5)]
    assert ids == [1, 2, 3, 4, 5]


def test_saida_pode_zerar_mas_nao_ficar_negativa(estoque):
    assert estoque.movimentar(105, "saida", 90, "Venda").quantidade_final == 0
    with pytest.raises(EstoqueError, match="Saldo insuficiente"):
        estoque.movimentar(105, "saida", 1, "Venda")
    assert estoque.buscar_produto(105).quantidade == 0


@pytest.mark.parametrize("quantidade", [0, -3, 1.5, "10", True, None])
def test_quantidade_invalida(estoque, quantidade):
    with pytest.raises(EstoqueError):
        estoque.movimentar(101, "entrada", quantidade, "Compra")


@pytest.mark.parametrize("descricao", ["", "   ", "x" * 101])
def test_descricao_invalida(estoque, descricao):
    with pytest.raises(EstoqueError):
        estoque.movimentar(101, "entrada", 1, descricao)


def test_produto_e_tipo_invalidos(estoque):
    with pytest.raises(EstoqueError, match="não encontrado"):
        estoque.movimentar(999, "entrada", 1, "Compra")
    with pytest.raises(EstoqueError, match="ENTRADA ou SA"):
        estoque.movimentar(101, "transferir", 1, "Compra")


def test_operacao_rejeitada_nao_gera_movimentacao(estoque):
    with pytest.raises(EstoqueError):
        estoque.movimentar(101, "saida", 10_000, "Venda")
    assert estoque.historico() == []


def test_persistencia_e_continuidade_do_id():
    Estoque.abrir().movimentar(101, "entrada", 10, "Compra")
    reaberto = Estoque.abrir()
    m = reaberto.movimentar(101, "saida", 5, "Venda")
    assert m.id == 2 and m.quantidade_final == 155
    assert [h.id for h in reaberto.historico()] == [1, 2]


def test_arquivo_mantem_formato_do_desafio(estoque):
    estoque.movimentar(101, "entrada", 1, "Compra")
    dados = json.loads(estoque.caminho.read_text(encoding="utf-8"))
    assert dados["estoque"][0] == {
        "codigoProduto": 101,
        "descricaoProduto": "Caneta Azul",
        "estoque": 151,
    }
    assert dados["movimentacoes"][0]["descricao"] == "Compra"


def test_resetar_restaura_saldos_e_apaga_historico(estoque):
    estoque.movimentar(101, "saida", 100, "Venda")
    estoque.resetar()
    assert estoque.buscar_produto(101).quantidade == 150
    assert estoque.historico() == []
    assert Estoque.abrir().historico() == []


def test_resetar_com_falha_na_gravacao_preserva_estado(estoque, monkeypatch):
    estoque.movimentar(101, "saida", 10, "Venda")

    def falha(*_args):
        raise OSError("sem espaço")

    monkeypatch.setattr("desafio.estoque._gravar_atomico", falha)
    with pytest.raises(DadosInvalidosError, match="Não foi possível gravar"):
        estoque.resetar()
    assert estoque.buscar_produto(101).quantidade == 140
    assert len(estoque.historico()) == 1


def test_arquivo_corrompido_gera_erro_de_dominio(tmp_path):
    pasta = tmp_path / "ruim"
    pasta.mkdir()
    (pasta / "estoque.json").write_text("{ não é json", encoding="utf-8")
    with pytest.raises(DadosInvalidosError):
        Estoque.abrir(pasta)


def test_codigos_repetidos_sao_rejeitados(tmp_path):
    pasta = tmp_path / "dup"
    pasta.mkdir()
    item = {"codigoProduto": 1, "descricaoProduto": "X", "estoque": 1}
    (pasta / "estoque.json").write_text(json.dumps({"estoque": [item, item]}), encoding="utf-8")
    with pytest.raises(DadosInvalidosError, match="repetidos"):
        Estoque.abrir(pasta)
