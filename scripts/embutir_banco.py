"""Gera lib/catalogo_db.js com o banco embutido (base64), para o index.html
abrir o catálogo automaticamente com duplo clique, sem servidor.
Uso: python embutir_banco.py catalogo_sistema.db lib/catalogo_db.js"""
import base64, sys
db, saida = sys.argv[1], sys.argv[2]
b64 = base64.b64encode(open(db, "rb").read()).decode()
with open(saida, "w", encoding="ascii") as f:
    f.write('window.CATALOGO_DB_B64="' + b64 + '";')
print(f"{saida}: {len(b64)/1e6:.1f} MB")
