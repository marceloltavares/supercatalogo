"""
Gera o banco catalogo_sistema.db a partir de:
  - CatalogoExpresso.c01  (base cifrada do Catálogo Cofap)
  - Passeio.xlsx          (árvore Sistema > Grupo > Subgrupo)

Uso:
  python gerar_banco.py CatalogoExpresso.c01 Passeio.xlsx catalogo_sistema.db

Requisitos: Python 3.9+, numpy, openpyxl
As regras de classificação ficam em REGRAS (abaixo) e também são gravadas
na tabela regra_classificacao, para consulta.
"""
import re
import sqlite3
import sys
import unicodedata
from collections import Counter

import numpy as np
from openpyxl import load_workbook

PAGE = 8192


# --------------------------------------------------------------------------
# 1. Decifrar o .c01 (SQLite com XOR de 8192 bytes por página)
# --------------------------------------------------------------------------
def decifrar(caminho_c01: str) -> bytes:
    raw = open(caminho_c01, "rb").read()
    pages = np.frombuffer(raw, np.uint8).reshape(-1, PAGE)
    # página vazia (folha 0x0D sem células) = página cifrada mais repetida
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


# --------------------------------------------------------------------------
# 2. Árvore do Passeio.xlsx
# --------------------------------------------------------------------------
def ler_arvore(caminho_xlsx: str):
    ws = load_workbook(caminho_xlsx, read_only=True, data_only=True)["Passeio"]
    nos, idx = [], {}
    sistema = grupo = None
    ordem = 0

    def add(nome, pai, nivel):
        nonlocal ordem
        chave = (pai, nome)
        if chave in idx:
            return idx[chave]
        ordem += 1
        nid = len(nos) + 1
        caminho = nome if pai is None else f"{nos[pai - 1]['caminho']} > {nome}"
        nos.append(dict(id=nid, pai=pai, nivel=nivel, nome=nome, caminho=caminho, ordem=ordem))
        idx[chave] = nid
        return nid

    for linha in ws.iter_rows(min_row=3, values_only=True):
        s, g, sg = [(str(v).strip() if v else None) for v in (list(linha) + [None] * 3)[:3]]
        if s:
            sistema = add(s, None, 1)
        if g and sistema:
            grupo = add(g, sistema, 2)
        if sg and grupo:
            add(sg, grupo, 3)
    return nos


# --------------------------------------------------------------------------
# 3. Regras de classificação Cofap -> árvore
#    (descrição do produto regex, posição regex, [(grupo, subgrupo), ...], obs)
#    A primeira regra que casar vale. Posição vazia = qualquer posição.
# --------------------------------------------------------------------------
D, T = r"DIANT", r"TRAS"
DT = r"DIANT.*TRAS"
REGRAS = [
    # Amortecedores
    (r"AMORTECEDOR", r"ESTICADOR", [("Correias e Polias", "Polias e Tensionadores")], "Amortecedor do tensionador"),
    (r"AMORTECEDOR", r"CAPÔ", [("Lataria", "Capô")], ""),
    (r"AMORTECEDOR", r"TAMPA TRASEIRA|CAÇAMBA", [("Lataria", "Tampa Traseira/Porta-malas")], ""),
    (r"AMORTECEDOR", r"BANCO", [("Acabamentos Internos", "Bancos (e Componentes)")], ""),
    (r"AMORTECEDOR", r"^" + DT, [("Suspensão Dianteira", "Amortecedores Dianteiros"),
                                 ("Suspensão Traseira", "Amortecedores Traseiros")], "Serve nas duas posições"),
    (r"AMORTECEDOR", r"^" + D, [("Suspensão Dianteira", "Amortecedores Dianteiros")], ""),
    (r"AMORTECEDOR", r"^" + T, [("Suspensão Traseira", "Amortecedores Traseiros")], ""),
    # Molas a gás
    (r"MOLA A GÁS", r"CAPÔ|TAMPA DO MOTOR|TAMPA DIANTEIRA", [("Lataria", "Capô")], ""),
    (r"MOLA A GÁS", r"PORTA MALAS|TAMPA TRASEIRA|PORTA TRASEIRA|BAGAGEIRO|VIDRO DA TAMPA",
     [("Lataria", "Tampa Traseira/Porta-malas")], ""),
    (r"MOLA A GÁS", r"GRADE", [("Para-choques e Grades", "Grade Frontal")], ""),
    (r"MOLA A GÁS", r"BANCO|CAMA", [("Acabamentos Internos", "Bancos (e Componentes)")], ""),
    # Bandejas, bieletas, barras
    (r"BANDEJA", D, [("Suspensão Dianteira", "Bandejas/Braços de Suspensão")], ""),
    (r"BANDEJA", T, [("Suspensão Traseira", "Braços de Suspensão Traseira (Multilink, etc.)")], ""),
    (r"BARRA DE DIREÇÃO|BRAÇO P.*MAN", "", [("Sistema de Direção", "Barras Axiais/Braços de Direção")], ""),
    (r"BIELETA.*", r"^" + DT, [("Suspensão Dianteira", "Bieletas Dianteiras"),
                               ("Suspensão Traseira", "Bieletas Traseiras")], ""),
    (r"BIELETA.*", D, [("Suspensão Dianteira", "Bieletas Dianteiras")], ""),
    (r"BIELETA.*", T, [("Suspensão Traseira", "Bieletas Traseiras")], ""),
    (r"KIT BARRA ESTABILIZADORA", D, [("Suspensão Dianteira", "Barra Estabilizadora Dianteira")], ""),
    (r"KIT BARRA ESTABILIZADORA", T, [("Suspensão Traseira", "Barra Estabilizadora Traseira")], ""),
    (r"BARRA DE TORÇÃO", "", [("Suspensão Traseira", "Eixo de Torção/Eixo Rígido")], ""),
    # Buchas, suportes, batentes
    (r"BUCHA", r"MOTOR", [("Coxins e Suportes do Motor", "Coxins do Motor")], ""),
    (r"BUCHA", r"DIREÇÃO", [("Sistema de Direção", "Caixa de Direção (Mecânica, Hidráulica, Elétrica)")], ""),
    (r"BUCHA", r"^" + DT, [("Suspensão Dianteira", "Buchas (Bandeja, Barra Estabilizadora)"),
                           ("Suspensão Traseira", "Buchas Traseiras")], ""),
    (r"BUCHA", D, [("Suspensão Dianteira", "Buchas (Bandeja, Barra Estabilizadora)")], ""),
    (r"BUCHA", T, [("Suspensão Traseira", "Buchas Traseiras")], ""),
    (r"SUPORTE", r"MOTOR", [("Coxins e Suportes do Motor", "Coxins do Motor")], ""),
    (r"SUPORTE", r"CÂMBIO", [("Coxins e Suportes da Transmissão", "Coxins do Câmbio")], ""),
    (r"SUPORTE", D, [("Suspensão Dianteira", "Coxins e Batentes do Amortecedor")], "Suporte/coxim do amortecedor"),
    (r"SUPORTE", T, [("Suspensão Traseira", "Buchas Traseiras")], "Árvore não tem nó de coxim traseiro"),
    (r"RESTRITOR DE TORQUE", "", [("Coxins e Suportes do Motor", "Coxins do Motor")], ""),
    (r"BATENTE|ISOLADOR|CALÇO|APOIO DE MOLA", "",
     [("Suspensão Dianteira", "Coxins e Batentes do Amortecedor")], ""),
    (r"(TOP )?KIT SUSPENSÃO", D, [("Suspensão Dianteira", "Coxins e Batentes do Amortecedor")], ""),
    (r"(TOP )?KIT SUSPENSÃO", T, [("Suspensão Traseira", "Amortecedores Traseiros")],
     "Kit batente/coifa traseiro; árvore não tem nó próprio"),
    # Molas
    (r"MOLA HELICOIDAL", D, [("Suspensão Dianteira", "Molas Helicoidais Dianteiras")], ""),
    (r"MOLA HELICOIDAL", T, [("Suspensão Traseira", "Molas Traseiras (Helicoidais, Feixe de Molas)")], ""),
    (r"FEIXE DE MOLA", T, [("Suspensão Traseira", "Molas Traseiras (Helicoidais, Feixe de Molas)")], ""),
    # Rodas, freios, direção, transmissão
    (r"CUBO DE RODA", "", [("Rodas e Pneus", "Cubos de Roda")], ""),
    (r"PASTILHA PARA FREIO", "", [("Freio a Disco", "Pastilhas de Freio")], ""),
    (r"PIVÔ DE SUSPENSÃO", "", [("Suspensão Dianteira", "Pivôs de Suspensão")], ""),
    (r"TERMINAL AXIAL", "", [("Sistema de Direção", "Barras Axiais/Braços de Direção")], ""),
    (r"TERMINAL DE DIREÇÃO", "", [("Sistema de Direção", "Terminais de Direção")], ""),
    (r"SEMIEIXO", "", [("Eixos de Transmissão e Homocinéticas", "Semieixos")], ""),
    (r"JUNTA HOMOCINÉTICA.*|KIT (DE )?REPARO.*|TRIZETA|TULIPA", "",
     [("Eixos de Transmissão e Homocinéticas", "Juntas Homocinéticas (Fixa, Deslizante)")], ""),
]


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


# --------------------------------------------------------------------------
# 4. Montagem do banco final
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE origem(chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE arvore(id INTEGER PRIMARY KEY, pai_id INTEGER REFERENCES arvore(id), nivel INTEGER,
                    nome TEXT, caminho TEXT, ordem INTEGER);
CREATE TABLE fabricante(id INTEGER PRIMARY KEY, nome TEXT, e_marca_peca INTEGER, e_montadora INTEGER);
CREATE TABLE produto(id INTEGER PRIMARY KEY, codigo TEXT, codigo_pesq TEXT, descricao TEXT,
                     grupo_cofap TEXT, linha TEXT, posicao TEXT, unidade TEXT,
                     foto TEXT, foto2 TEXT, foto3 TEXT, observacao TEXT, texto_busca TEXT);
CREATE TABLE aplicacao(id INTEGER PRIMARY KEY, montadora_id INTEGER REFERENCES fabricante(id),
                       modelo TEXT, complemento TEXT, anos TEXT, complemento3 TEXT, complemento4 TEXT);
CREATE TABLE produto_aplicacao(produto_id INTEGER REFERENCES produto(id),
                               aplicacao_id INTEGER REFERENCES aplicacao(id),
                               PRIMARY KEY(produto_id, aplicacao_id));
CREATE TABLE referencia_cruzada(id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produto(id),
                                marca_id INTEGER REFERENCES fabricante(id), codigo TEXT, codigo_pesq TEXT);
CREATE TABLE regra_classificacao(id INTEGER PRIMARY KEY, descricao_regex TEXT, posicao_regex TEXT,
                                 destinos TEXT, observacao TEXT);
CREATE TABLE produto_arvore(produto_id INTEGER REFERENCES produto(id),
                            arvore_id INTEGER REFERENCES arvore(id),
                            regra_id INTEGER REFERENCES regra_classificacao(id),
                            PRIMARY KEY(produto_id, arvore_id));
CREATE TABLE distribuidor(id INTEGER PRIMARY KEY, nome TEXT, latitude TEXT, longitude TEXT,
                          logradouro TEXT, numero TEXT, complemento TEXT, bairro TEXT, cidade TEXT,
                          cep TEXT, uf TEXT, contato TEXT, email TEXT, telefone TEXT);
CREATE INDEX ix_pa_aplic ON produto_aplicacao(aplicacao_id);
CREATE INDEX ix_ref_prod ON referencia_cruzada(produto_id);
CREATE INDEX ix_ref_pesq ON referencia_cruzada(codigo_pesq);
CREATE INDEX ix_parv_arv ON produto_arvore(arvore_id);
CREATE INDEX ix_aplic_mont ON aplicacao(montadora_id);
CREATE INDEX ix_prod_pesq ON produto(codigo_pesq);
CREATE VIEW v_produto_sem_classificacao AS
  SELECT p.* FROM produto p WHERE NOT EXISTS (SELECT 1 FROM produto_arvore a WHERE a.produto_id = p.id);
"""


def main(c01, xlsx, saida):
    src = sqlite3.connect(":memory:")
    src.deserialize(decifrar(c01))
    src.create_collation("NO_CASE_2", nocase)

    import os
    if os.path.exists(saida):
        os.remove(saida)
    db = sqlite3.connect(saida)
    db.executescript(SCHEMA)
    db.create_function("remove_acento", 1, sem_acento)

    um = src.execute("SELECT DataEmissao, Versao, VersaoCatalogo FROM UMREGISTRO").fetchone()
    db.executemany("INSERT INTO origem VALUES(?,?)", [
        ("fonte", os.path.basename(c01)), ("data_emissao", um[0]),
        ("versao", str(um[1])), ("versao_catalogo", str(um[2])), ("arvore", os.path.basename(xlsx))])

    # árvore
    nos = ler_arvore(xlsx)
    db.executemany("INSERT INTO arvore VALUES(:id,:pai,:nivel,:nome,:caminho,:ordem)", nos)
    sub_por_grupo = {}
    for n in nos:
        if n["nivel"] == 3:
            g = nos[n["pai"] - 1]["nome"]
            sub_por_grupo[(g, n["nome"])] = n["id"]

    # fabricantes, produtos, aplicações, referências
    db.executemany("INSERT INTO fabricante VALUES(?,?,?,?)",
                   src.execute("SELECT CodigoFabricante, DescricaoFabricante, FlagProduto, FlagAplicacao FROM FABRICANTE"))
    grupos = dict(src.execute("SELECT CodigoGrupoProduto, DescricaoGrupoProduto FROM GRUPOPRODUTO"))
    obs = dict(src.execute("SELECT CodigoProduto, Observacao FROM PRODUTO_OBS"))
    produtos = []
    for r in src.execute("""SELECT CodigoProduto, NumeroProduto, NumeroProdutoPesq, DescricaoProduto, CodigoGrupoProduto,
                                   CpoAuxProd1, CpoAuxProd2, Unidade, ArquivoFotoProduto, ArquivoFotoProduto2,
                                   ArquivoFotoProduto3, PCs FROM PRODUTO"""):
        pid, cod, pesq, desc, gid, linha, pos, un, f1, f2, f3, pcs = r
        produtos.append((pid, cod, pesq, desc, grupos.get(gid), linha, pos, un, f1, f2, f3,
                         obs.get(pid), sem_acento(pcs)))
    db.executemany("INSERT INTO produto VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", produtos)
    db.executemany("INSERT INTO aplicacao VALUES(?,?,?,?,?,?,?)", src.execute(
        """SELECT CodigoAplicacao, CodigoFabricante, DescricaoAplicacao, ComplementoAplicacao,
                  ComplementoAplicacao2, ComplementoAplicacao3, ComplementoAplicacao4 FROM APLICACAO"""))
    db.executemany("INSERT INTO produto_aplicacao VALUES(?,?)",
                   src.execute("SELECT CodigoProduto, CodigoAplicacao FROM PRODUTO_APLICACAO"))
    db.executemany("INSERT INTO referencia_cruzada VALUES(?,?,?,?,?)", src.execute(
        "SELECT CodigoReferenciaCruzada, CodigoProduto, CodigoFabricante, NumeroProduto, NumeroProdutoPesq FROM REFERENCIACRUZADA"))
    # texto de busca: texto original + descrição/posição + marca e código de cada referência cruzada
    db.execute("""UPDATE produto SET texto_busca = texto_busca || ' ' || upper(coalesce(descricao,'') || ' ' ||
                  coalesce(linha,'') || ' ' || coalesce(posicao,'')) || ' ' || coalesce((
                  SELECT group_concat(upper(f.nome || ' ' || r.codigo), ' ') FROM referencia_cruzada r
                  LEFT JOIN fabricante f ON f.id = r.marca_id WHERE r.produto_id = produto.id), '')""")
    db.execute("UPDATE produto SET texto_busca = remove_acento(texto_busca)")
    db.executemany("INSERT INTO distribuidor VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", src.execute(
        """SELECT CodDistr, NomeDistr, Latitude, Longitude, TipoEndereco || ' ' || Endereco, NroEndereco,
                  Complemento, Bairro, Cidade, CEP, UF, Contato, Email, Telefone FROM DISTRIBUIDORES"""))

    # regras + classificação
    for i, (dre, pre, dest, ob) in enumerate(REGRAS, 1):
        for d in dest:
            if d not in sub_por_grupo:
                raise SystemExit(f"Regra {i}: nó não encontrado na árvore: {d}")
        db.execute("INSERT INTO regra_classificacao VALUES(?,?,?,?,?)",
                   (i, dre, pre, " | ".join(f"{g} > {s}" for g, s in dest), ob))
    comp = [(i, re.compile(r"^(" + dre + r")$"), re.compile(pre) if pre else None, dest)
            for i, (dre, pre, dest, _) in enumerate(REGRAS, 1)]
    ligacoes = []
    for pid, _, _, desc, _, _, pos, *_ in produtos:
        desc, pos = (desc or "").strip(), (pos or "").strip()
        for i, dre, pre, dest in comp:
            if dre.match(desc) and (pre is None or pre.search(pos)):
                ligacoes += [(pid, sub_por_grupo[d], i) for d in dest]
                break
    db.executemany("INSERT OR IGNORE INTO produto_arvore VALUES(?,?,?)", ligacoes)
    db.commit()

    total = db.execute("SELECT COUNT(*) FROM produto").fetchone()[0]
    sem = db.execute("SELECT COUNT(*) FROM v_produto_sem_classificacao").fetchone()[0]
    print(f"Produtos: {total} | classificados: {total - sem} | sem classificação: {sem}")
    db.execute("VACUUM")
    db.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
