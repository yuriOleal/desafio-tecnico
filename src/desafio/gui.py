"""Interface gráfica (tkinter) com uma aba para cada exercício."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from desafio import __version__
from desafio.comissoes import calcular_comissoes, carregar_vendas
from desafio.erros import DesafioError
from desafio.estoque import Estoque, TipoMovimentacao
from desafio.formatacao import formatar_brl, ler_data, ler_valor
from desafio.juros import calcular_juros

SUGESTOES = {
    TipoMovimentacao.ENTRADA: [
        "Compra",
        "Devolução de cliente",
        "Transferência recebida",
        "Ajuste de inventário",
    ],
    TipoMovimentacao.SAIDA: [
        "Venda",
        "Perda/avaria",
        "Transferência enviada",
        "Ajuste de inventário",
    ],
}


def _data_br(iso: str) -> str:
    """'2026-10-05T11:41:00' -> '05/10/2026 11:41:00'."""
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M:%S")


def main() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("Esta instalação do Python não inclui tkinter; use a interface de linha de comando.")
        return 1

    class Aplicacao(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title(f"Desafio Técnico - Desenvolvedor/a de Sistemas Jr. (v{__version__})")
            self.geometry("1020x640")
            self.minsize(960, 560)
            self.estoque = Estoque.abrir()

            abas = ttk.Notebook(self)
            abas.pack(fill="both", expand=True, padx=8, pady=8)
            self._montar_comissoes(abas)
            self._montar_estoque(abas)
            self._montar_juros(abas)

        # ------------------------------------------------------------ utilitários
        def _erro(self, erro: Exception) -> None:
            messagebox.showerror("Atenção", str(erro), parent=self)

        @staticmethod
        def _tabela(pai, colunas, altura=10):
            """colunas: lista de (id, título, largura, alinhamento)."""
            quadro = ttk.Frame(pai)
            tabela = ttk.Treeview(
                quadro, columns=[c[0] for c in colunas], show="headings", height=altura
            )
            for ident, titulo, largura, alinhamento in colunas:
                tabela.heading(ident, text=titulo)
                tabela.column(ident, width=largura, anchor=alinhamento)
            rolagem = ttk.Scrollbar(quadro, orient="vertical", command=tabela.yview)
            tabela.configure(yscrollcommand=rolagem.set)
            tabela.pack(side="left", fill="both", expand=True)
            rolagem.pack(side="right", fill="y")
            return quadro, tabela

        # --------------------------------------------------------- aba 1: comissões
        def _montar_comissoes(self, abas: "ttk.Notebook") -> None:
            aba = ttk.Frame(abas, padding=12)
            abas.add(aba, text="1. Comissões")
            self.arquivo_vendas: Path | None = None

            topo = ttk.Frame(aba)
            topo.pack(fill="x")
            ttk.Button(topo, text="Abrir JSON de vendas…", command=self._abrir_vendas).pack(
                side="left"
            )
            ttk.Button(topo, text="Usar dados do desafio", command=self._usar_vendas_padrao).pack(
                side="left", padx=6
            )
            self.rotulo_origem = ttk.Label(topo, text="")
            self.rotulo_origem.pack(side="left", padx=10)

            quadro, self.tabela_comissoes = self._tabela(
                aba,
                [
                    ("vendedor", "Vendedor", 240, "w"),
                    ("vendas", "Vendas", 80, "e"),
                    ("total", "Total vendido", 180, "e"),
                    ("comissao", "Comissão", 160, "e"),
                ],
            )
            quadro.pack(fill="both", expand=True, pady=10)
            self.rotulo_total_comissoes = ttk.Label(aba, font=("TkDefaultFont", 11, "bold"))
            self.rotulo_total_comissoes.pack(anchor="e")
            ttk.Label(
                aba,
                justify="left",
                text="Regra por venda: abaixo de R$ 100,00 = sem comissão · "
                "de R$ 100,00 a R$ 499,99 = 1% · a partir de R$ 500,00 = 5%",
            ).pack(anchor="w", pady=(8, 0))
            self._carregar_comissoes(None)

        def _abrir_vendas(self) -> None:
            caminho = filedialog.askopenfilename(
                parent=self,
                title="Selecione o JSON de vendas",
                filetypes=[("JSON", "*.json"), ("Todos os arquivos", "*.*")],
            )
            if caminho:
                self._carregar_comissoes(Path(caminho))

        def _usar_vendas_padrao(self) -> None:
            self._carregar_comissoes(None)

        def _carregar_comissoes(self, caminho: Path | None) -> None:
            try:
                resumos = calcular_comissoes(carregar_vendas(caminho))
            except DesafioError as erro:
                self._erro(erro)
                return
            self.rotulo_origem.config(text=f"Origem: {caminho or 'dados do desafio'}")
            self.tabela_comissoes.delete(*self.tabela_comissoes.get_children())
            for r in resumos:
                self.tabela_comissoes.insert(
                    "",
                    "end",
                    values=(
                        r.vendedor,
                        r.quantidade_vendas,
                        formatar_brl(r.total_vendido),
                        formatar_brl(r.comissao),
                    ),
                )
            total = sum((r.comissao for r in resumos), Decimal("0"))
            self.rotulo_total_comissoes.config(text=f"Total de comissões: {formatar_brl(total)}")

        # ----------------------------------------------------------- aba 2: estoque
        def _montar_estoque(self, abas: "ttk.Notebook") -> None:
            aba = ttk.Frame(abas, padding=12)
            abas.add(aba, text="2. Estoque")

            esquerda = ttk.Frame(aba)
            esquerda.pack(side="left", fill="y", padx=(0, 12))
            form = ttk.LabelFrame(esquerda, text="Nova movimentação", padding=10)
            form.pack(fill="x")

            self.var_produto = tk.StringVar()
            self.var_tipo = tk.StringVar(value=TipoMovimentacao.ENTRADA.value)
            self.var_quantidade = tk.StringVar(value="1")
            self.var_descricao = tk.StringVar()

            ttk.Label(form, text="Produto").grid(row=0, column=0, sticky="w")
            self.combo_produto = ttk.Combobox(
                form, textvariable=self.var_produto, state="readonly", width=34
            )
            self.combo_produto.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

            ttk.Label(form, text="Tipo").grid(row=2, column=0, sticky="w")
            tipos = ttk.Frame(form)
            tipos.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
            for tipo in TipoMovimentacao:
                ttk.Radiobutton(
                    tipos,
                    text=tipo.rotulo,
                    value=tipo.value,
                    variable=self.var_tipo,
                    command=self._atualizar_sugestoes,
                ).pack(side="left", padx=(0, 12))

            ttk.Label(form, text="Quantidade").grid(row=4, column=0, sticky="w")
            ttk.Spinbox(
                form, from_=1, to=1_000_000, textvariable=self.var_quantidade, width=10
            ).grid(row=5, column=0, sticky="w", pady=(0, 8))

            ttk.Label(form, text="Descrição da movimentação").grid(row=6, column=0, sticky="w")
            self.combo_descricao = ttk.Combobox(form, textvariable=self.var_descricao, width=34)
            self.combo_descricao.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))

            ttk.Button(form, text="Registrar movimentação", command=self._registrar).grid(
                row=8, column=0, columnspan=2, sticky="ew"
            )
            self.rotulo_resultado = ttk.Label(
                esquerda, wraplength=290, justify="left", font=("TkDefaultFont", 10, "bold")
            )
            self.rotulo_resultado.pack(fill="x", pady=12)
            ttk.Button(esquerda, text="Restaurar estoque original", command=self._resetar).pack(
                side="bottom", fill="x"
            )

            direita = ttk.Frame(aba)
            direita.pack(side="left", fill="both", expand=True)
            ttk.Label(direita, text="Saldos atuais").pack(anchor="w")
            quadro, self.tabela_produtos = self._tabela(
                direita,
                [
                    ("codigo", "Código", 70, "center"),
                    ("produto", "Produto", 230, "w"),
                    ("estoque", "Estoque", 80, "e"),
                ],
                altura=6,
            )
            quadro.pack(fill="x", pady=(0, 10))
            ttk.Label(direita, text="Histórico de movimentações").pack(anchor="w")
            quadro, self.tabela_historico = self._tabela(
                direita,
                [
                    ("id", "Nº", 36, "center"),
                    ("data", "Data/hora", 165, "w"),
                    ("produto", "Produto", 120, "w"),
                    ("tipo", "Tipo", 55, "w"),
                    ("qtde", "Qtde", 45, "e"),
                    ("descricao", "Descrição", 105, "w"),
                    ("saldo", "Saldo", 50, "e"),
                ],
                altura=8,
            )
            quadro.pack(fill="both", expand=True)
            self._atualizar_estoque()
            self._atualizar_sugestoes()

        def _atualizar_sugestoes(self) -> None:
            self.combo_descricao.config(values=SUGESTOES[TipoMovimentacao(self.var_tipo.get())])

        def _atualizar_estoque(self) -> None:
            produtos = self.estoque.produtos()
            self.combo_produto.config(values=[f"{p.codigo} - {p.descricao}" for p in produtos])
            if produtos and not self.var_produto.get():
                self.combo_produto.current(0)
            self.tabela_produtos.delete(*self.tabela_produtos.get_children())
            for p in produtos:
                self.tabela_produtos.insert("", "end", values=(p.codigo, p.descricao, p.quantidade))
            self.tabela_historico.delete(*self.tabela_historico.get_children())
            for m in reversed(self.estoque.historico()):
                self.tabela_historico.insert(
                    "",
                    "end",
                    values=(
                        m.id,
                        _data_br(m.data_hora),
                        m.produto,
                        m.tipo.rotulo,
                        m.quantidade,
                        m.descricao,
                        m.quantidade_final,
                    ),
                )

        def _registrar(self) -> None:
            try:
                codigo = int(self.var_produto.get().split(" - ")[0])
                quantidade = int(self.var_quantidade.get())
            except ValueError:
                self._erro(DesafioError("Selecione um produto e informe uma quantidade inteira."))
                return
            try:
                m = self.estoque.movimentar(
                    codigo,
                    TipoMovimentacao(self.var_tipo.get()),
                    quantidade,
                    self.var_descricao.get(),
                )
            except DesafioError as erro:
                self._erro(erro)
                return
            self.rotulo_resultado.config(
                text=f"Movimentação nº {m.id} registrada.\n"
                f"Quantidade final de '{m.produto}': {m.quantidade_final}"
            )
            self._atualizar_estoque()

        def _resetar(self) -> None:
            if messagebox.askyesno(
                "Confirmar", "Restaurar os saldos originais e apagar o histórico?", parent=self
            ):
                try:
                    self.estoque.resetar()
                except DesafioError as erro:
                    self._erro(erro)
                    return
                self.rotulo_resultado.config(text="Estoque restaurado.")
                self._atualizar_estoque()

        # ------------------------------------------------------------ aba 3: juros
        def _montar_juros(self, abas: "ttk.Notebook") -> None:
            aba = ttk.Frame(abas, padding=16)
            abas.add(aba, text="3. Juros por atraso")
            form = ttk.Frame(aba)
            form.pack(anchor="w")

            self.var_valor = tk.StringVar()
            self.var_vencimento = tk.StringVar()
            self.var_hoje = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))

            campos = [
                ("Valor (R$)", self.var_valor, "ex.: 1.500,00"),
                ("Data de vencimento", self.var_vencimento, "dd/mm/aaaa"),
                ("Calcular até", self.var_hoje, "dd/mm/aaaa (padrão: hoje)"),
            ]
            for linha, (rotulo, variavel, dica) in enumerate(campos):
                ttk.Label(form, text=rotulo).grid(row=linha, column=0, sticky="w", pady=4)
                entrada = ttk.Entry(form, textvariable=variavel, width=22)
                entrada.grid(row=linha, column=1, padx=8)
                entrada.bind("<Return>", lambda _e: self._calcular_juros())
                ttk.Label(form, text=dica, foreground="gray").grid(row=linha, column=2, sticky="w")
            ttk.Button(form, text="Calcular", command=self._calcular_juros).grid(
                row=3, column=1, sticky="w", padx=8, pady=10
            )

            self.rotulo_juros = ttk.Label(aba, justify="left", font=("TkDefaultFont", 11))
            self.rotulo_juros.pack(anchor="w", pady=10)
            ttk.Label(
                aba,
                text="Juros simples de 2,5% ao dia: juros = valor × 2,5% × dias em atraso.",
                foreground="gray",
            ).pack(anchor="w")

        def _calcular_juros(self) -> None:
            try:
                valor = ler_valor(self.var_valor.get())
                vencimento = ler_data(self.var_vencimento.get())
                hoje = ler_data(self.var_hoje.get()) if self.var_hoje.get().strip() else None
                r = calcular_juros(valor, vencimento, hoje)
            except DesafioError as erro:
                self._erro(erro)
                return
            self.rotulo_juros.config(
                text=f"Dias em atraso: {r.dias_em_atraso}\n"
                f"Juros: {formatar_brl(r.juros)}\n"
                f"Total a pagar: {formatar_brl(r.total)}"
            )

    try:
        Aplicacao().mainloop()
    except DesafioError as erro:
        print(f"Erro: {erro}")
        return 1
    except tk.TclError as erro:
        print(f"Não foi possível abrir a interface gráfica: {erro}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
