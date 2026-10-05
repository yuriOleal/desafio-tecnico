"""Interface de linha de comando.

desafio comissoes [-a vendas.json] [--json]
desafio estoque [listar|entrada|saida|historico|resetar|interativo]
desafio juros [VALOR VENCIMENTO] [--hoje dd/mm/aaaa]
desafio gui
"""

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path

from desafio import __version__
from desafio.comissoes import calcular_comissoes, carregar_vendas
from desafio.erros import DesafioError
from desafio.estoque import Estoque, Movimentacao, TipoMovimentacao
from desafio.formatacao import formatar_brl, ler_data, ler_valor
from desafio.juros import calcular_juros


# --------------------------------------------------------------------------- comissões
def _cmd_comissoes(args: argparse.Namespace) -> int:
    resumos = calcular_comissoes(carregar_vendas(args.arquivo))
    total = sum((r.comissao for r in resumos), Decimal("0"))

    if args.json:
        saida = {
            "vendedores": [
                {
                    "vendedor": r.vendedor,
                    "quantidade_vendas": r.quantidade_vendas,
                    "total_vendido": str(r.total_vendido),
                    "comissao": str(r.comissao),
                }
                for r in resumos
            ],
            "total_comissoes": str(total),
        }
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0

    print(f"{'Vendedor':<18}{'Vendas':>7}{'Total vendido':>18}{'Comissão':>14}")
    print("-" * 57)
    for r in resumos:
        print(
            f"{r.vendedor:<18}{r.quantidade_vendas:>7}"
            f"{formatar_brl(r.total_vendido):>18}{formatar_brl(r.comissao):>14}"
        )
    print("-" * 57)
    print(f"{'Total de comissões':<43}{formatar_brl(total):>14}")
    return 0


# ----------------------------------------------------------------------------- estoque
def _imprimir_produtos(estoque: Estoque) -> None:
    print(f"\n{'Código':<8}{'Produto':<30}{'Estoque':>8}")
    print("-" * 46)
    for p in estoque.produtos():
        print(f"{p.codigo:<8}{p.descricao:<30}{p.quantidade:>8}")
    print()


def _imprimir_historico(estoque: Estoque) -> None:
    historico = estoque.historico()
    if not historico:
        print("Nenhuma movimentação registrada.")
        return
    print(
        f"{'Nº':<5}{'Data/hora':<21}{'Produto':<27}{'Tipo':<9}{'Qtde':>6}  "
        f"{'Descrição':<22}{'Saldo':>6}"
    )
    print("-" * 98)
    for m in historico:
        print(
            f"{m.id:<5}{m.data_hora.replace('T', ' '):<21}{m.produto:<27}{m.tipo.rotulo:<9}"
            f"{m.quantidade:>6}  {m.descricao[:21]:<22}{m.quantidade_final:>6}"
        )


def _imprimir_resultado(m: Movimentacao) -> None:
    print(
        f"\nMovimentação nº {m.id} registrada: {m.tipo.rotulo} de {m.quantidade} "
        f"× {m.produto} ({m.descricao})."
    )
    print(f"Quantidade final em estoque de '{m.produto}': {m.quantidade_final}\n")


def _ler_inteiro(pergunta: str, entrada: Callable[[str], str]) -> int:
    while True:
        try:
            return int(entrada(pergunta).strip())
        except ValueError:
            print("Valor inválido, digite um número inteiro.")


def menu_interativo(estoque: Estoque, entrada: Callable[[str], str] = input) -> int:
    """Menu de console. `entrada` é injetável para facilitar os testes."""
    try:
        while True:
            print(
                "=== Estoque ===\n1) Listar produtos\n2) Entrada de mercadoria\n"
                "3) Saída de mercadoria\n4) Histórico\n0) Sair"
            )
            opcao = entrada("Opção: ").strip()
            if opcao == "0":
                return 0
            if opcao == "1":
                _imprimir_produtos(estoque)
            elif opcao == "4":
                _imprimir_historico(estoque)
            elif opcao in ("2", "3"):
                tipo = TipoMovimentacao.ENTRADA if opcao == "2" else TipoMovimentacao.SAIDA
                _imprimir_produtos(estoque)
                codigo = _ler_inteiro("Código do produto: ", entrada)
                quantidade = _ler_inteiro("Quantidade: ", entrada)
                descricao = entrada("Descrição da movimentação (ex.: Compra, Venda, Devolução): ")
                try:
                    _imprimir_resultado(estoque.movimentar(codigo, tipo, quantidade, descricao))
                except DesafioError as erro:
                    print(f"\n[ERRO] {erro}\n")
            else:
                print("Opção inválida.\n")
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


def _cmd_estoque(args: argparse.Namespace) -> int:
    estoque = Estoque.abrir(args.dados_dir)
    acao = args.acao or "interativo"
    if acao == "listar":
        _imprimir_produtos(estoque)
    elif acao in ("entrada", "saida"):
        movimentacao = estoque.movimentar(
            args.produto, TipoMovimentacao.de_texto(acao), args.quantidade, args.descricao
        )
        _imprimir_resultado(movimentacao)
    elif acao == "historico":
        _imprimir_historico(estoque)
    elif acao == "resetar":
        estoque.resetar()
        print("Estoque restaurado para os valores originais do desafio.")
    else:
        return menu_interativo(estoque)
    return 0


# ------------------------------------------------------------------------------ juros
def _cmd_juros(args: argparse.Namespace) -> int:
    texto_valor = args.valor if args.valor is not None else input("Valor (ex.: 1.500,00): ")
    texto_data = (
        args.vencimento
        if args.vencimento is not None
        else input("Data de vencimento (dd/mm/aaaa): ")
    )
    valor = ler_valor(texto_valor)
    vencimento = ler_data(texto_data)
    hoje = ler_data(args.hoje) if args.hoje else None

    r = calcular_juros(valor, vencimento, hoje)
    print(f"\nValor original:   {formatar_brl(r.valor)}")
    print(f"Vencimento:       {r.vencimento:%d/%m/%Y}")
    print(f"Dias em atraso:   {r.dias_em_atraso}")
    print(f"Juros (2,5%/dia): {formatar_brl(r.juros)}")
    print(f"Total a pagar:    {formatar_brl(r.total)}")
    return 0


# -------------------------------------------------------------------------------- gui
def _cmd_gui(_: argparse.Namespace) -> int:
    from desafio.gui import main as main_gui

    return main_gui()


# ------------------------------------------------------------------------------ parser
def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="desafio",
        description="Desafio técnico - Desenvolvedor/a de Sistemas Jr.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO")

    p = sub.add_parser("comissoes", help="1) comissão por vendedor a partir de um JSON de vendas")
    p.add_argument("-a", "--arquivo", type=Path, help="JSON de vendas (padrão: dados do desafio)")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.set_defaults(func=_cmd_comissoes)

    p = sub.add_parser("estoque", help="2) movimentações de estoque (menu interativo por padrão)")
    p.add_argument("--dados-dir", type=Path, help="pasta onde o estoque é guardado")
    acoes = p.add_subparsers(dest="acao", metavar="AÇÃO")
    acoes.add_parser("listar", help="lista produtos e saldos")
    acoes.add_parser("historico", help="lista as movimentações registradas")
    acoes.add_parser("resetar", help="volta aos saldos originais do desafio")
    acoes.add_parser("interativo", help="menu interativo")
    for nome, ajuda in (
        ("entrada", "dá entrada de mercadoria"),
        ("saida", "dá saída de mercadoria"),
    ):
        a = acoes.add_parser(nome, help=ajuda)
        a.add_argument("-p", "--produto", type=int, required=True, help="código do produto")
        a.add_argument("-q", "--quantidade", type=int, required=True, help="quantidade (> 0)")
        a.add_argument("-d", "--descricao", required=True, help='ex.: "Compra", "Venda"')
    p.set_defaults(func=_cmd_estoque)

    p = sub.add_parser("juros", help="3) juros por atraso (2,5%% ao dia)")
    p.add_argument("valor", nargs="?", help="ex.: 1500, 1500,50 ou 1.500,50")
    p.add_argument("vencimento", nargs="?", help="dd/mm/aaaa")
    p.add_argument("--hoje", help="data de referência dd/mm/aaaa (padrão: hoje)")
    p.set_defaults(func=_cmd_juros)

    p = sub.add_parser("gui", help="abre a interface gráfica")
    p.set_defaults(func=_cmd_gui)
    return parser


def _tolerar_codificacao_do_console() -> None:
    """Evita UnicodeEncodeError em consoles com codepage legada (ex.: cmd.exe com cp850)."""
    for fluxo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if reconfigurar:
            reconfigurar(errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _tolerar_codificacao_do_console()
    parser = criar_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except DesafioError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
