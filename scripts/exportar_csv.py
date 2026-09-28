"""Exporta cada tabela do catalogo_sistema.db para CSV (UTF-8 com BOM, separador ;),
pronto para importar no Microsoft Access (Dados Externos > Arquivo de Texto).
Uso: python exportar_csv.py catalogo_sistema.db pasta_saida"""
import csv, os, sqlite3, sys
db, saida = sys.argv[1], sys.argv[2]
os.makedirs(saida, exist_ok=True)
c = sqlite3.connect(db)
for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
    cur = c.execute(f"SELECT * FROM [{t}]")
    with open(os.path.join(saida, t + ".csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow([d[0] for d in cur.description]); w.writerows(cur)
    print(t)
