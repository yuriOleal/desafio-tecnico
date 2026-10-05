"""Exercício 2 - Movimentação de estoque.

Cada movimentação (ENTRADA ou SAÍDA) possui:
  - um número identificador único (sequencial, nunca reutilizado);
  - uma descrição do tipo da movimentação (ex.: "Compra", "Venda", "Devolução");
e, ao final, devolve a quantidade final em estoque do produto movimentado.

O estado (saldos + histórico) fica em um único arquivo JSON, gravado de forma atômica,
que mantém o formato do desafio (`codigoProduto`, `descricaoProduto`, `estoque`).
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from importlib import resources
from pathlib import Path

from desafio.erros import DadosInvalidosError, EstoqueError

NOME_ARQUIVO = "estoque.json"
TAMANHO_MAXIMO_DESCRICAO = 100


class TipoMovimentacao(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"

    @property
    def rotulo(self) -> str:
        return "Entrada" if self is TipoMovimentacao.ENTRADA else "Saída"

    @classmethod
    def de_texto(cls, texto: str) -> "TipoMovimentacao":
        normalizado = texto.strip().upper().replace("Í", "I")
        try:
            return cls(normalizado)
        except ValueError:
            raise EstoqueError("Tipo de movimentação deve ser ENTRADA ou SAÍDA.") from None


@dataclass
class Produto:
    codigo: int
    descricao: str
    quantidade: int

    def para_json(self) -> dict:
        return {
            "codigoProduto": self.codigo,
            "descricaoProduto": self.descricao,
            "estoque": self.quantidade,
        }


@dataclass(frozen=True)
class Movimentacao:
    id: int
    data_hora: str
    codigo_produto: int
    produto: str
    tipo: TipoMovimentacao
    quantidade: int
    descricao: str
    quantidade_final: int

    def para_json(self) -> dict:
        dados = asdict(self)
        dados["tipo"] = self.tipo.value
        return dados


def diretorio_dados() -> Path:
    """Onde o estado do estoque é guardado (funciona igual no script e no executável).

    Pode ser sobrescrito com a variável de ambiente DESAFIO_DADOS_DIR.
    """
    if override := os.environ.get("DESAFIO_DADOS_DIR"):
        return Path(override)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "desafio-tecnico"


def _ler_semente() -> str:
    return resources.files("desafio").joinpath("dados/estoque.json").read_text("utf-8")


class Estoque:
    def __init__(self, caminho: Path, produtos: list[Produto], movimentacoes: list[Movimentacao]):
        self.caminho = caminho
        self._produtos = produtos
        self._movimentacoes = movimentacoes

    # ------------------------------------------------------------------ persistência

    @classmethod
    def abrir(cls, diretorio: Path | None = None) -> "Estoque":
        """Abre o estoque do diretório; na primeira execução cria a partir do JSON do desafio."""
        diretorio = Path(diretorio) if diretorio else diretorio_dados()
        caminho = diretorio / NOME_ARQUIVO
        try:
            if not caminho.exists():
                diretorio.mkdir(parents=True, exist_ok=True)
                _gravar_atomico(caminho, _ler_semente())
            conteudo = caminho.read_text(encoding="utf-8")
        except OSError as erro:
            raise DadosInvalidosError(f"Não foi possível acessar {caminho}: {erro}.") from erro
        produtos, movimentacoes = _interpretar(conteudo, caminho)
        return cls(caminho, produtos, movimentacoes)

    def _salvar(self) -> None:
        conteudo = json.dumps(
            {
                "estoque": [p.para_json() for p in self._produtos],
                "movimentacoes": [m.para_json() for m in self._movimentacoes],
            },
            ensure_ascii=False,
            indent=2,
        )
        _gravar_atomico(self.caminho, conteudo)

    def resetar(self) -> None:
        """Volta aos saldos originais do desafio e apaga o histórico."""
        anteriores = self._produtos, self._movimentacoes
        self._produtos, self._movimentacoes = _interpretar(_ler_semente(), self.caminho)
        try:
            self._salvar()
        except OSError as erro:
            self._produtos, self._movimentacoes = anteriores
            raise DadosInvalidosError(f"Não foi possível gravar {self.caminho}: {erro}.") from erro

    # ------------------------------------------------------------------ consultas

    def produtos(self) -> list[Produto]:
        return list(self._produtos)

    def historico(self) -> list[Movimentacao]:
        return list(self._movimentacoes)

    def buscar_produto(self, codigo: int) -> Produto:
        for produto in self._produtos:
            if produto.codigo == codigo:
                return produto
        raise EstoqueError(f"Produto {codigo} não encontrado.")

    # ------------------------------------------------------------------ operação

    def movimentar(
        self, codigo: int, tipo: TipoMovimentacao | str, quantidade: int, descricao: str
    ) -> Movimentacao:
        """Registra uma entrada ou saída e devolve a movimentação (com a quantidade final)."""
        if isinstance(tipo, str):
            tipo = TipoMovimentacao.de_texto(tipo)
        if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade <= 0:
            raise EstoqueError("A quantidade deve ser um número inteiro maior que zero.")
        descricao = descricao.strip()
        if not descricao:
            raise EstoqueError("A descrição da movimentação é obrigatória.")
        if len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
            raise EstoqueError(
                f"A descrição deve ter no máximo {TAMANHO_MAXIMO_DESCRICAO} caracteres."
            )

        produto = self.buscar_produto(codigo)
        if tipo is TipoMovimentacao.SAIDA and quantidade > produto.quantidade:
            raise EstoqueError(
                f"Saldo insuficiente para '{produto.descricao}': "
                f"disponível {produto.quantidade}, solicitado {quantidade}."
            )

        saldo_anterior = produto.quantidade
        produto.quantidade += quantidade if tipo is TipoMovimentacao.ENTRADA else -quantidade
        movimentacao = Movimentacao(
            id=max((m.id for m in self._movimentacoes), default=0) + 1,
            data_hora=datetime.now().isoformat(timespec="seconds"),
            codigo_produto=produto.codigo,
            produto=produto.descricao,
            tipo=tipo,
            quantidade=quantidade,
            descricao=descricao,
            quantidade_final=produto.quantidade,
        )
        self._movimentacoes.append(movimentacao)
        try:
            self._salvar()
        except OSError as erro:
            # Desfaz em memória para não divergir do arquivo.
            produto.quantidade = saldo_anterior
            self._movimentacoes.pop()
            raise DadosInvalidosError(f"Não foi possível gravar {self.caminho}: {erro}.") from erro
        return movimentacao


def _gravar_atomico(caminho: Path, conteudo: str) -> None:
    """Grava em arquivo temporário e troca de nome, evitando arquivo corrompido em caso de falha."""
    nome_tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=caminho.parent, suffix=".tmp", delete=False
        ) as tmp:
            nome_tmp = tmp.name
            tmp.write(conteudo)
        os.replace(nome_tmp, caminho)
    finally:
        if nome_tmp and os.path.exists(nome_tmp):
            os.unlink(nome_tmp)


def _interpretar(conteudo: str, origem: Path) -> tuple[list[Produto], list[Movimentacao]]:
    try:
        dados = json.loads(conteudo)
        produtos = [
            Produto(int(p["codigoProduto"]), str(p["descricaoProduto"]), int(p["estoque"]))
            for p in dados["estoque"]
        ]
        movimentacoes = [
            Movimentacao(
                id=int(m["id"]),
                data_hora=str(m["data_hora"]),
                codigo_produto=int(m["codigo_produto"]),
                produto=str(m["produto"]),
                tipo=TipoMovimentacao(m["tipo"]),
                quantidade=int(m["quantidade"]),
                descricao=str(m["descricao"]),
                quantidade_final=int(m["quantidade_final"]),
            )
            for m in dados.get("movimentacoes", [])
        ]
    except (ValueError, KeyError, TypeError) as erro:
        raise DadosInvalidosError(f"Arquivo de estoque inválido ({origem}): {erro!r}.") from erro
    if len({p.codigo for p in produtos}) != len(produtos):
        raise DadosInvalidosError(f"Arquivo de estoque inválido ({origem}): códigos repetidos.")
    return produtos, movimentacoes
