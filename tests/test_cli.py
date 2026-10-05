import json

import pytest

from desafio.cli import main, menu_interativo
from desafio.estoque import Estoque


def executar(capsys, *argv):
    codigo = main(list(argv))
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def test_sem_argumentos_mostra_ajuda(capsys):
    codigo, out, _ = executar(capsys)
    assert codigo == 0 and "COMANDO" in out


def test_versao(capsys):
    with pytest.raises(SystemExit) as saida:
        main(["--version"])
    assert saida.value.code == 0
    assert "desafio 1.0.0" in capsys.readouterr().out


def test_comissoes_tabela(capsys):
    codigo, out, _ = executar(capsys, "comissoes")
    assert codigo == 0
    assert "João Silva" in out and "R$ 495,68" in out and "R$ 1.745,98" in out


def test_comissoes_json(capsys):
    codigo, out, _ = executar(capsys, "comissoes", "--json")
    dados = json.loads(out)
    assert codigo == 0 and dados["total_comissoes"] == "1745.98"
    assert dados["vendedores"][0] == {
        "vendedor": "João Silva",
        "quantidade_vendas": 10,
        "total_vendido": "10754.70",
        "comissao": "495.68",
    }


def test_comissoes_arquivo_inexistente(capsys, tmp_path):
    codigo, _, err = executar(capsys, "comissoes", "-a", str(tmp_path / "x.json"))
    assert codigo == 1 and err.startswith("Erro:")


def test_estoque_movimentacao_ponta_a_ponta(capsys):
    codigo, out, _ = executar(capsys, "estoque", "saida", "-p", "101", "-q", "30", "-d", "Venda")
    assert codigo == 0 and "Movimentação nº 1" in out and ": 120" in out
    codigo, out, _ = executar(capsys, "estoque", "entrada", "-p", "101", "-q", "5", "-d", "Compra")
    assert "Movimentação nº 2" in out and ": 125" in out
    _, out, _ = executar(capsys, "estoque", "historico")
    assert "Venda" in out and "Compra" in out


def test_estoque_saldo_insuficiente_retorna_erro(capsys):
    codigo, _, err = executar(capsys, "estoque", "saida", "-p", "101", "-q", "999", "-d", "Venda")
    assert codigo == 1 and "Saldo insuficiente" in err


def test_estoque_listar_e_resetar(capsys):
    executar(capsys, "estoque", "saida", "-p", "101", "-q", "30", "-d", "Venda")
    codigo, out, _ = executar(capsys, "estoque", "resetar")
    assert codigo == 0 and "restaurado" in out
    _, out, _ = executar(capsys, "estoque", "listar")
    assert "Caneta Azul" in out and "150" in out


def test_menu_interativo(capsys):
    respostas = iter(["3", "101", "abc", "40", "Venda", "3", "101", "9999", "Venda", "4", "9", "0"])
    codigo = menu_interativo(Estoque.abrir(), entrada=lambda _p: next(respostas))
    out = capsys.readouterr().out
    assert codigo == 0
    assert "Quantidade final em estoque de 'Caneta Azul': 110" in out
    assert "digite um número inteiro" in out  # 'abc' foi tratado
    assert "[ERRO] Saldo insuficiente" in out
    assert "Opção inválida" in out


def test_menu_encerra_com_fim_de_entrada(capsys):
    def sem_entrada(_prompt):
        raise EOFError

    assert menu_interativo(Estoque.abrir(), entrada=sem_entrada) == 0


def test_juros(capsys):
    codigo, out, _ = executar(capsys, "juros", "1.000,00", "24/09/2026", "--hoje", "04/10/2026")
    assert codigo == 0
    assert "Dias em atraso:   10" in out and "R$ 250,00" in out and "R$ 1.250,00" in out


def test_juros_entrada_invalida(capsys):
    codigo, _, err = executar(capsys, "juros", "abc", "01/01/2026")
    assert codigo == 1 and "Valor inválido" in err
    codigo, _, err = executar(capsys, "juros", "100", "32/13/2026")
    assert codigo == 1 and "Data inválida" in err
