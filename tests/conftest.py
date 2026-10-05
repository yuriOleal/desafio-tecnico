import pytest


@pytest.fixture(autouse=True)
def dados_isolados(tmp_path, monkeypatch):
    """Cada teste usa uma pasta de dados própria, nunca a do usuário."""
    monkeypatch.setenv("DESAFIO_DADOS_DIR", str(tmp_path / "dados"))
