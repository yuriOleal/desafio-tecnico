"""Gera os executáveis (um arquivo só, sem precisar de Python instalado) com PyInstaller.

    pip install -e ".[build]"
    python scripts/build.py

Saída em dist/:
    desafio      (desafio.exe no Windows)      -> linha de comando
    desafio-gui  (desafio-gui.exe no Windows)  -> interface gráfica, sem janela de console

O PyInstaller não faz compilação cruzada: o executável é do sistema em que o build roda.
Para gerar o .exe sem ter Windows, use o workflow .github/workflows/release.yml.
"""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "src" / "desafio" / "dados"


def pyinstaller(nome: str, entrada: str, *, janela: bool) -> None:
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        "--name", nome,
        "--paths", str(RAIZ / "src"),
        "--add-data", f"{DADOS}{os.pathsep}desafio/dados",
        "--specpath", str(RAIZ / "build"),
        "--distpath", str(RAIZ / "dist"),
        "--workpath", str(RAIZ / "build" / nome),
    ]  # fmt: skip
    if janela:
        comando.append("--windowed")
    comando.append(str(RAIZ / "scripts" / entrada))
    print("->", " ".join(comando))
    subprocess.run(comando, check=True)


def main() -> None:
    pyinstaller("desafio", "entry_cli.py", janela=False)
    pyinstaller("desafio-gui", "entry_gui.py", janela=True)

    sufixo = ".exe" if os.name == "nt" else ""
    cli = RAIZ / "dist" / f"desafio{sufixo}"
    print("\nTeste rápido do executável:")
    subprocess.run([str(cli), "--version"], check=True)
    subprocess.run([str(cli), "comissoes"], check=True)
    print(f"\nExecutáveis gerados em {RAIZ / 'dist'}")


if __name__ == "__main__":
    main()
