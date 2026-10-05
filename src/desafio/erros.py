"""Exceções de domínio. Todas herdam de DesafioError, o que simplifica o tratamento na CLI/GUI."""


class DesafioError(Exception):
    """Erro esperado, com mensagem pronta para ser mostrada ao usuário."""


class DadosInvalidosError(DesafioError):
    """Arquivo ou entrada com formato/valores inválidos."""


class EstoqueError(DesafioError):
    """Violação de regra de negócio do estoque (produto inexistente, saldo insuficiente...)."""
