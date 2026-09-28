"""
Atualiza o catálogo inteiro depois de instalar versões novas dos programas da Cofap / Magneti Marelli.

Uso (na pasta catalogo):
  python scripts\\atualizar_catalogo.py
  python scripts\\atualizar_catalogo.py --origem C:\\ProgramData

Passos:
  1. gerar_banco.py     -> catalogo_sistema.db (produtos, aplicações, árvores, marcas)
  2. recuperar_fotos.py -> FotoProd\\ (só converte as fotos novas ou alteradas)
  3. informativos.py    -> Informativos\\, OCR, lib\\catalogo_db.js e ?v= do index.html
"""
import argparse
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from gerar_banco import BASES  # noqa: E402


def rodar(*args):
    print("\n>>", " ".join(os.path.basename(a) if a.endswith(".py") else a for a in args), flush=True)
    r = subprocess.run([sys.executable, *args])
    if r.returncode:
        raise SystemExit(f"Falhou: {' '.join(args)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", default=r"C:\ProgramData")
    a = ap.parse_args()
    rodar(os.path.join(AQUI, "gerar_banco.py"), "--origem", a.origem)
    for b in BASES:
        fotos = os.path.join(a.origem, b["pasta"], "FotoProd")
        if os.path.isdir(fotos):
            rodar(os.path.join(AQUI, "recuperar_fotos.py"), fotos, os.path.join(RAIZ, "FotoProd"))
    rodar(os.path.join(AQUI, "informativos.py"), "--origem", a.origem)
    print("\nPronto. Confira o index.html e suba os arquivos (ver LEIAME.md).")


if __name__ == "__main__":
    main()
