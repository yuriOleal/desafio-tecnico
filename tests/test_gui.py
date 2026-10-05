"""Teste de fumaça da interface gráfica (pulado se não houver tkinter ou display)."""

import pytest

tk = pytest.importorskip("tkinter")


def _aplicacao_disponivel():
    try:
        raiz = tk.Tk()
    except tk.TclError:
        return False
    raiz.destroy()
    return True


pytestmark = pytest.mark.skipif(not _aplicacao_disponivel(), reason="sem display gráfico")


def test_gui_fluxo_basico(monkeypatch):
    from tkinter import messagebox

    import desafio.gui as gui

    erros = []
    monkeypatch.setattr(messagebox, "showerror", lambda _t, msg, **_k: erros.append(msg))

    def roteiro(self, n=0):
        self.update()
        assert len(self.tabela_comissoes.get_children()) == 4
        assert "1.745,98" in self.rotulo_total_comissoes.cget("text")

        self.combo_produto.current(0)
        self.var_tipo.set("SAIDA")
        self.var_quantidade.set("20")
        self.var_descricao.set("Venda")
        self._registrar()
        assert "130" in self.rotulo_resultado.cget("text")
        assert len(self.tabela_historico.get_children()) == 1

        self.var_quantidade.set("9999")
        self._registrar()
        assert "Saldo insuficiente" in erros[-1]

        self.var_valor.set("1.000,00")
        self.var_vencimento.set("24/09/2026")
        self.var_hoje.set("04/10/2026")
        self._calcular_juros()
        assert "R$ 250,00" in self.rotulo_juros.cget("text")
        self.destroy()

    monkeypatch.setattr(tk.Tk, "mainloop", roteiro)
    assert gui.main() == 0
