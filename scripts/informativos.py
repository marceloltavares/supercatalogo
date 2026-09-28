"""
Inclui os INFORMATIVOS TÉCNICOS de todas as bases (Cofap, Linha Pesada, Magneti Marelli,
Motocicletas) no catalogo_sistema.db.

Uso (rodar DEPOIS do gerar_banco.py, a partir da pasta catalogo):
  python scripts\informativos.py
  python scripts\informativos.py --origem C:\ProgramData --saida catalogo_sistema.db

O que faz:
  1. Lê a tabela INFORMATIVO do .c01 de cada base usada no banco (lista BASES do gerar_banco.py).
  2. Converte os .img para Informativos/<codigo>.jpg ao lado do index.html (+ miniatura em
     Informativos/mini/). Os .img são JPEG comuns (sem cifra). Informativos da Cofap mantêm o
     código original; os das outras bases somam o offset da base (ex.: 1000412).
  3. Lê o texto de cada imagem por OCR (Tesseract) e guarda em scripts/informativos_ocr.json.
     Só roda OCR para o que ainda não está no cache — sem Tesseract, usa o cache e avisa.
  4. Liga informativo -> produto pelos códigos que aparecem na imagem (produto.codigo_pesq).
     Código só com números só vale se o tipo de peça do título bater com o produto.
  5. Grava as tabelas informativo e informativo_produto, regrava lib/catalogo_db.js e troca
     o ?v= no index.html.

Requisitos: Python 3.9+, numpy, Pillow (opcional, melhora o OCR e gera miniaturas) e
Tesseract OCR (opcional, só para informativos novos).
"""
import base64
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter

import argparse

import numpy as np

PAGE = 8192
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)                       # pasta catalogo (index.html)
PASTA_JPG = os.path.join(RAIZ, "Informativos")
CACHE_OCR = os.path.join(AQUI, "informativos_ocr.json")

# Correções manuais (CodigoInformativo -> valor)
TITULO_CORRIGIDO = {
    1205: "Mola a Gás - Mitsubishi / Renault",     # no .c01 está "Amortecedor"; a imagem é de mola a gás
}
CODIGOS_EXTRAS = {}      # ex.: {1151: ["JHC55004"]} para forçar ligação que o OCR não pegou
CODIGOS_IGNORAR = {}     # ex.: {1234: ["GP12345"]} para descartar ligação errada

# Tipo de peça do título -> regex na descrição do produto (para conferir)
TIPOS = [
    ("AMORTECEDOR", r"AMORTECEDOR"), ("MOLA A GAS", r"MOLA A GAS"), ("MOLA HELICOIDAL", r"MOLA HELICOIDAL"),
    ("PIVO", r"PIVO"), ("BIELETA", r"BIELETA"), ("SEMIEIXO", r"SEMIEIXO"), ("CUBO", r"CUBO"),
    ("TERMINAL AXIAL", r"TERMINAL AXIAL"), ("TERMINAL DE DIRECAO", r"TERMINAL DE DIRECAO"),
    ("JUNTA", r"JUNTA|KIT|TRIZETA|TULIPA"), ("KIT REPARO", r"KIT|JUNTA|TRIZETA|TULIPA"),
    ("KIT", r"KIT|BATENTE|COIFA"), ("BANDEJA", r"BANDEJA"), ("BUCHA", r"BUCHA|SUPORTE"),
]
# Uniformiza nomes de categoria vindos do título
CATEGORIAS = {"Kit Suspensão": "Kit de Suspensão", "Top Kit Suspensão": "Top Kit de Suspensão",
              "Kit Reparo de Junta": "Kit Reparo de Junta Homocinética"}


# --------------------------------------------------------------------------
def decifrar(caminho_c01: str) -> bytes:
    raw = open(caminho_c01, "rb").read()
    pages = np.frombuffer(raw, np.uint8).reshape(-1, PAGE)
    vazia = Counter(p.tobytes() for p in pages[1:]).most_common(1)[0][0]
    plano = np.zeros(PAGE, np.uint8)
    plano[0], plano[5] = 0x0D, 0x20
    chave = np.frombuffer(vazia, np.uint8) ^ plano
    dec = (pages ^ chave).tobytes()
    if dec[:16] != b"SQLite format 3\x00":
        raise SystemExit("Não foi possível decifrar o arquivo .c01")
    return dec


def nocase(a, b):
    a, b = a.lower(), b.lower()
    return (a > b) - (a < b)


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


def formato(b: bytes) -> str:
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:4] == b"%PDF":
        return "pdf"
    if b[:5] == b"#C3p:":
        return "c3p"
    return "?"


# --------------------------------------------------------------------------
def achar_tesseract():
    t = shutil.which("tesseract")
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if not t and os.path.exists(c):
            t = c
    return t


def ocr(tess, caminho):
    """Duas passadas: página inteira e imagem ampliada 3x (pega os códigos grandes)."""
    textos = []
    r = subprocess.run([tess, caminho, "-", "--psm", "3"], capture_output=True)
    textos.append(r.stdout.decode("utf-8", "ignore"))
    try:
        from PIL import Image
        im = Image.open(caminho).convert("L")
        im = im.resize((im.width * 3, im.height * 3))
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.png")
            im.save(p)
            r = subprocess.run([tess, p, "-", "--psm", "11"], capture_output=True)
            textos.append(r.stdout.decode("utf-8", "ignore"))
    except ImportError:
        pass
    return "\n".join(textos)


TOKEN = re.compile(r"\b[A-Z0-9]{3,12}(?:[.\-][A-Z0-9]{1,8}){1,2}\b|\b[A-Z0-9]{1,5}[.\-]?\s?[A-Z0-9]{3,8}\b")
TROCA = str.maketrans("OIlSZB", "011528")


def candidatos(tok):
    k = re.sub(r"[^A-Z0-9]", "", tok)
    out = [k]
    m = re.match(r"^([A-Z]*)(.*)$", k)
    out.append(m.group(1) + m.group(2).translate(TROCA))
    m = re.match(r"^([A-Z]{2,3})(O?)(.*)$", k)
    if m:
        out.append(m.group(1) + m.group(2).replace("O", "0") + re.sub(r"O(?=\d)|(?<=\d)O", "0", m.group(3)))
    out.append(re.sub(r"(?<=[A-Z]{3})O", "0", k))
    return list(dict.fromkeys(out))


def tipo_confere(titulo, descricao, grupo=""):
    t, d = sem_acento(titulo), sem_acento(f"{descricao} {grupo}")
    for chave, rx in TIPOS:
        if chave in t.split(" - ")[0]:
            return bool(re.search(rx, d))
    # categorias sem regra fixa (ex.: Magneti Marelli): alguma palavra do título no produto
    cat = t.split(" - ")[0]
    radicais = {w[:5] for w in re.findall(r"[A-Z]{4,}", cat)}
    return any(r in d for r in radicais)


# --------------------------------------------------------------------------
SCHEMA = """
DROP VIEW IF EXISTS v_informativo_sem_produto;
DROP TABLE IF EXISTS informativo_produto;
DROP TABLE IF EXISTS informativo;
CREATE TABLE informativo(id INTEGER PRIMARY KEY, numero TEXT, data TEXT, titulo TEXT, ordem INTEGER,
                         tipo_arquivo TEXT, arquivo_origem TEXT, categoria_cofap TEXT,
                         categoria TEXT, montadoras TEXT, imagem TEXT, texto_ocr TEXT, texto_busca TEXT,
                         marca TEXT, base TEXT);
CREATE TABLE informativo_produto(informativo_id INTEGER REFERENCES informativo(id),
                                 produto_id INTEGER REFERENCES produto(id),
                                 codigo_lido TEXT, confere_tipo INTEGER, origem TEXT,
                                 PRIMARY KEY(informativo_id, produto_id));
CREATE INDEX ix_infprod_prod ON informativo_produto(produto_id);
CREATE VIEW v_informativo_sem_produto AS
  SELECT i.* FROM informativo i WHERE NOT EXISTS (SELECT 1 FROM informativo_produto x WHERE x.informativo_id = i.id);
"""


def main(origem, saida):
    # 1. origem: bases que estão no banco (chaves base_<id> gravadas pelo gerar_banco.py)
    sys.path.insert(0, AQUI)
    from gerar_banco import BASES
    con = sqlite3.connect(f"file:{saida}?mode=ro", uri=True)
    no_banco = {k[5:] for (k,) in con.execute("SELECT chave FROM origem WHERE chave LIKE 'base\\_%' ESCAPE '\\'")} or {"cofap"}
    con.close()
    infs = []
    with tempfile.TemporaryDirectory() as tmp:
        for b in BASES:
            if b["id"] not in no_banco:
                continue
            pasta = os.path.join(origem, b["pasta"])
            p = os.path.join(tmp, b["id"] + ".db")
            open(p, "wb").write(decifrar(os.path.join(pasta, "Configuracoes", "CatalogoExpresso.c01")))
            src = sqlite3.connect(p)
            src.create_collation("NO_CASE_2", nocase)
            marca = b["marca"] if isinstance(b["marca"], str) else None
            rows = src.execute("""SELECT CodigoInformativo, NumeroInformativo, DataInformativo, TituloInformativo,
                                         OrdemInformativo, TipoInformativo, ArquivoInformativo, CategoriaInformativo
                                  FROM INFORMATIVO ORDER BY OrdemInformativo""").fetchall()
            src.close()
            infs += [(cid + b["offset"], *r, os.path.join(pasta, "Informativos"), b["id"], marca) for cid, *r in rows]
            print(f"Informativos {b['nome']}: {len(rows)}")

    # 2. imagens
    os.makedirs(PASTA_JPG, exist_ok=True)
    imagens, problemas = {}, []
    for cid, _n, _d, _t, _o, _tp, arq, _cat, pasta_img, _b, _m in infs:
        origem = os.path.join(pasta_img, arq or "")
        if not arq or not os.path.exists(origem):
            problemas.append(f"{cid}: arquivo não encontrado ({arq})")
            continue
        b = open(origem, "rb").read()
        fmt = formato(b)
        if fmt in ("c3p", "?"):
            problemas.append(f"{cid}: formato não reconhecido ({b[:8]!r}) — não convertido")
            continue
        nome = f"{cid}.{fmt}"
        destino = os.path.join(PASTA_JPG, nome)
        if not (os.path.exists(destino) and open(destino, "rb").read() == b):
            open(destino, "wb").write(b)
        imagens[cid] = (nome, hashlib.md5(b).hexdigest(), destino)
        # miniatura para a lista (Informativos/mini/<codigo>.jpg); sem Pillow a página usa a imagem inteira
        mini = os.path.join(PASTA_JPG, "mini", f"{cid}.jpg")
        if fmt != "pdf" and (not os.path.exists(mini) or os.path.getmtime(mini) < os.path.getmtime(destino)):
            try:
                from PIL import Image
                os.makedirs(os.path.dirname(mini), exist_ok=True)
                im = Image.open(destino).convert("RGB")
                im.thumbnail((160, 240))
                im.save(mini, "JPEG", quality=80, optimize=True)
            except ImportError:
                pass
    print(f"Imagens em {PASTA_JPG}: {len(imagens)}")

    # 3. OCR com cache
    cache = json.load(open(CACHE_OCR, encoding="utf-8")) if os.path.exists(CACHE_OCR) else {}
    tess = achar_tesseract()
    faltam = [cid for cid, (_, md5, _) in imagens.items() if cache.get(str(cid), {}).get("md5") != md5]
    if faltam and tess:
        print(f"OCR em {len(faltam)} imagem(ns)...")
        for i, cid in enumerate(faltam, 1):
            nome, md5, destino = imagens[cid]
            if nome.endswith(".pdf"):
                continue
            cache[str(cid)] = {"md5": md5, "texto": ocr(tess, destino)}
            if i % 10 == 0 or i == len(faltam):
                json.dump(cache, open(CACHE_OCR, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
                print(f"  {i}/{len(faltam)}")
    elif faltam:
        problemas.append(f"Tesseract não encontrado: {len(faltam)} informativo(s) sem OCR "
                         f"({', '.join(map(str, faltam[:10]))}...). Instale o Tesseract ou use CODIGOS_EXTRAS.")

    # 4. banco (trabalha numa cópia temporária e regrava o arquivo no fim)
    tmpdir = tempfile.mkdtemp()
    trabalho = os.path.join(tmpdir, "catalogo.db")
    shutil.copyfile(saida, trabalho)
    db = sqlite3.connect(trabalho)
    db.executescript(SCHEMA)
    prods = {}
    for pid, pesq, desc, grupo, marca_p in db.execute("SELECT id, upper(codigo_pesq), descricao, grupo_cofap, marca FROM produto"):
        prods.setdefault(pesq, []).append((pid, desc, grupo, marca_p))
    linhas_inf, ligacoes, conferir = [], [], []
    for cid, num, data, tit, ordem, tipo, arq, cat, _pasta, bid, marca in infs:
        tit = re.sub(r"\s+", " ", TITULO_CORRIGIDO.get(cid, tit or "")).strip()
        partes = [x.strip() for x in tit.split(" - ", 1)]
        categoria = CATEGORIAS.get(partes[0], partes[0])
        montadoras = " / ".join(x.strip() for x in partes[1].split("/")) if len(partes) > 1 else ""
        texto = cache.get(str(cid), {}).get("texto", "")
        img = imagens.get(cid, (None,))[0]
        achados = {}
        for m in TOKEN.finditer(texto.upper()):
            for c in candidatos(m.group()):
                if c in prods:
                    achados.setdefault(c, "ocr")
                    break
        for c in CODIGOS_EXTRAS.get(cid, []):
            achados[re.sub(r"[^A-Z0-9]", "", c.upper())] = "manual"
        for c in CODIGOS_IGNORAR.get(cid, []):
            achados.pop(re.sub(r"[^A-Z0-9]", "", c.upper()), None)
        cods, marcas = [], Counter()
        for c, origem in achados.items():
            for pid, desc, grupo, marca_p in prods.get(c, []):
                ok = tipo_confere(tit, desc, grupo)
                if origem == "ocr" and not ok and c.isdigit():
                    continue            # código só numérico sem bater o tipo: descarta
                if not ok:
                    conferir.append(f"{num} ({cid}) {tit} -> {c} {desc}")
                ligacoes.append((cid, pid, c, int(ok), origem))
                cods.append(c)
                marcas[marca_p] += 1
        busca = sem_acento(" ".join([num, tit, categoria, montadoras, " ".join(cods), texto]))
        busca = re.sub(r"\s+", " ", busca)
        linhas_inf.append((cid, num, (data or "")[:10], tit, ordem, tipo, arq, cat or None, categoria,
                           montadoras, img and f"Informativos/{img}", texto, busca,
                           marca or (marcas.most_common(1)[0][0] if marcas else None), bid))
    db.executemany("INSERT INTO informativo VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", linhas_inf)
    db.executemany("INSERT OR IGNORE INTO informativo_produto VALUES(?,?,?,?,?)", ligacoes)
    db.execute("DELETE FROM origem WHERE chave = 'informativos'")
    db.execute("INSERT INTO origem VALUES('informativos', ?)", (str(len(linhas_inf)),))
    db.commit()
    sem = db.execute("SELECT numero, id, titulo FROM v_informativo_sem_produto ORDER BY ordem").fetchall()
    nlig = db.execute("SELECT COUNT(*) FROM informativo_produto").fetchone()[0]
    db.execute("VACUUM")
    db.close()
    with open(saida, "wb") as f:
        f.write(open(trabalho, "rb").read())
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"Ligações informativo->produto: {nlig} | informativos sem produto: {len(sem)}")
    for s in sem:
        print("  sem produto:", *s)
    for c in conferir:
        print("  conferir tipo:", c)
    for p in problemas:
        print("  AVISO:", p)

    # 5. banco embutido + ?v= no index.html
    js = os.path.join(RAIZ, "lib", "catalogo_db.js")
    b64 = base64.b64encode(open(saida, "rb").read()).decode()
    with open(js, "w", encoding="ascii") as f:
        f.write('window.CATALOGO_DB_B64="' + b64 + '";')
    print(f"{js}: {len(b64) / 1e6:.1f} MB")
    html = os.path.join(RAIZ, "index.html")
    if os.path.exists(html):
        s = open(html, encoding="utf-8").read()
        # ?v=AAAAMMDD; se já estiver com a data de hoje, acrescenta b, c, d... para furar o cache
        hoje = dt.date.today().strftime("%Y%m%d")
        m = re.search(r"lib/catalogo_db\.js\?v=(\w+)", s)
        atual = m.group(1) if m else ""
        v = hoje
        if atual.startswith(hoje):
            suf = atual[len(hoje):]
            v = hoje + (chr(ord(suf[-1]) + 1) if suf else "b")
        s2 = re.sub(r"(lib/catalogo_db\.js\?v=)\w+", r"\g<1>" + v, s)
        if s2 != s:
            open(html, "w", encoding="utf-8", newline="\n").write(s2)
        print(f"index.html: catalogo_db.js?v={v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", default=r"C:\ProgramData", help="pasta onde estão os catálogos instalados")
    ap.add_argument("--saida", default=os.path.join(RAIZ, "catalogo_sistema.db"))
    a = ap.parse_args()
    main(a.origem, a.saida)
