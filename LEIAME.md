# Catálogo de peças — Cofap e Magneti Marelli

Página única (`index.html`), sem servidor. O banco SQLite vai embutido em `lib/catalogo_db.js` e abre sozinho,
com duplo clique no arquivo ou publicado no GitHub Pages.

## Como usar
1. Abra o `index.html` no Chrome ou Edge (ou o endereço publicado). O catálogo carrega sozinho.
   Se `lib/catalogo_db.js` não existir, a página pede o `catalogo_sistema.db` (botão ou arrastar).
2. Escolha a linha nas abas (Passeio, Caminhão, Ônibus, Trator, Moto) e navegue pela árvore Sistema > Grupo > Subgrupo.
   Filtre por **marca** (Cofap, Magneti Marelli), montadora e modelo, e busque por código, código de concorrente ou texto.
   Cada produto mostra a etiqueta da marca.
3. **Informativos** (botão no cabeçalho): lançamentos técnicos das duas marcas, com filtro por marca, categoria, ano e
   mês e busca por título, número, código de produto ou veículo. Clicar num produto do informativo abre o detalhe dele.
   No detalhe do produto aparece a seção **Informativos técnicos**.

O cabeçalho mostra o período das bases ("Bases de 21/05 a 16/09/2026"). Passe o mouse para ver a data de cada uma.
O botão **Fotos** (só ao abrir pelo arquivo, não no site) permite apontar outra pasta de fotos.

## Bases usadas
Todas vêm do programa Catálogo Expresso (Ideia 2001), instalado em `C:\ProgramData`:

| Base | Pasta | Como entra |
|---|---|---|
| Cofap | `CatalogoProdutosCofap` | base principal (marca Cofap) |
| Cofap Linha Pesada | `CatalogoCofapAmortecedores-LinhaPesada` | mesclada na Cofap: só entra o que falta (aplicações de montadora + modelo novas para o produto, referências e informativos) |
| Magneti Marelli | `CatalogoProdutosMagnetiMarelli` | marca Magneti Marelli |
| Motocicletas | `CatalogoProdutosCofapMagnetiMarelliMotocicletas` | aba Moto. Marca pelo código: com "MM" (baterias, relés, velas, reguladores, sensores, filtros) = Magneti Marelli; o resto (amortecedores, bengalas, cabos, freios, kits) = Cofap |

Situação em 28/09/2026: 7.112 produtos Cofap e 6.831 Magneti Marelli, 58.921 aplicações, 337 informativos
(500 ligações com produtos) e 13.962 fotos.

## Conteúdo
| Arquivo | Função |
|---|---|
| `index.html` + `lib/` | Interface (sql.js embutido, lê o banco direto no navegador) |
| `lib/catalogo_db.js` | Banco embutido em base64 (24 MB; cerca de 7 MB comprimido pelo GitHub Pages), carregado como `catalogo_db.js?v=AAAAMMDD` |
| `catalogo_sistema.db` | Banco SQLite completo |
| `FotoProd/` | Fotos dos produtos (JPG, nomes em minúsculas) |
| `Informativos/`, `Informativos/mini/` | Imagens e miniaturas dos informativos |
| `arvores/` | Árvores Passeio, Caminhão, Ônibus, Trator e Moto (.xlsx) |
| `scripts/atualizar_catalogo.py` | **Atualiza tudo em sequência** (banco, fotos, informativos) |
| `scripts/gerar_banco.py` | Lê as bases e as árvores e gera o `catalogo_sistema.db` (inclui as regras de classificação da Cofap) |
| `scripts/regras_marcas.py` | Regras da Magneti Marelli e das Motocicletas, equivalências nas árvores de Caminhão, Ônibus e Trator, linha por montadora e marca das peças de moto |
| `scripts/linha_aplicacao.csv` | Linha (Passeio/Caminhão/...) de cada aplicação e como foi decidida. Pode ser editada |
| `scripts/informativos.py` | Converte os informativos, lê os códigos por OCR, grava as tabelas, regrava o `catalogo_db.js` e troca o `?v=` |
| `scripts/informativos_ocr.json` | Cache do OCR (não apague: evita precisar do Tesseract para os informativos já lidos) |
| `scripts/recuperar_fotos.py` | Converte as fotos do programa (formato `#C3p:`) para JPG. Pula as já convertidas |
| `scripts/embutir_banco.py`, `exportar_csv.py` | Banco embutido avulso e exportação CSV para o Access |
| `csv_access/` | CSVs para o Access (gerados em 24/09, antes das linhas e marcas; ver "Usar no Access") |

## Atualizar (novas versões dos programas)
Atualize os programas Cofap / Magneti Marelli e, na pasta `catalogo`, rode:

```
python scripts\atualizar_catalogo.py
```

Ele roda, em ordem, `gerar_banco.py`, `recuperar_fotos.py` (para cada base) e `informativos.py`, e troca o `?v=` do
`index.html` (data de hoje; se já estiver com a data de hoje, vira `AAAAMMDDb`, `c`...). Sem trocar o `?v=` o navegador
pode mostrar o banco antigo do cache. Se os programas estiverem em outro lugar: `--origem D:\Pasta`.

Requisitos: Python 3.9+, `numpy`, `openpyxl`, `Pillow`. O **Tesseract OCR** só é necessário para informativos novos
(instalador para Windows: https://github.com/UB-Mannheim/tesseract/wiki). Sem ele, o script usa o cache e avisa quais
ficaram sem leitura.

## Como os produtos entram nas linhas e na árvore
**Linha de cada aplicação** (nesta ordem):
1. base com linha fixa (Motocicletas = Moto);
2. `scripts/linha_aplicacao.csv`: decisão já tomada para aquela montadora + modelo + complementos;
3. `LINHA_MONTADORA` em `regras_marcas.py` (ex.: Caterpillar, Massey Ferguson → Trator; MWM, Cummins → Caminhão; Caio, Volare → Ônibus);
4. regra geral: palavras (ÔNIBUS, CAMINHÃO, TRATOR...), mesmo modelo, padrão do modelo ou montadora já conhecidos; sem nada disso, Passeio.

A coluna `decisao` do CSV mostra qual regra decidiu. Para corrigir uma aplicação, troque o número da coluna `linha` e rode de novo.
O produto aparece em todas as linhas das suas aplicações.

**Classificação na árvore:**
- Cofap: `REGRAS_COFAP` em `gerar_banco.py` (descrição + posição → subgrupo, por linha).
- Magneti Marelli e Motocicletas: `regras_marcas.py` (grupo do catálogo + descrição → subgrupo da Passeio ou da Moto), e
  `EQUIVALENTES` para o subgrupo correspondente em Caminhão, Ônibus e Trator.
- O que não casa com nenhuma regra fica em **Sem classificação** da linha (view `v_produto_sem_classificacao`).

Pendências conhecidas de classificação:
- A árvore **Ônibus não tem sistema de arrefecimento**. Radiadores, bombas d'água, mangueiras e válvulas termostáticas
  Magneti Marelli ficam em Sem classificação nessa linha. Para resolver, inclua o sistema no `Onibus.xlsx` e as
  equivalências em `regras_marcas.py`.
- Peças de ignição (velas, bobinas, cabos) com aplicação em Caminhão ou Trator ficam sem classificação, porque a árvore
  diesel não tem esses nós.

## Informativos técnicos
- Origem: tabela `INFORMATIVO` de cada base + arquivos `.img` da pasta `Informativos` de cada programa. São JPEG comuns.
- Os da Cofap mantêm o código original (ex.: `Informativos/1130.jpg`). Os das outras bases somam o offset da base
  (Magneti Marelli 1.000.000, Motocicletas 2.000.000, Linha Pesada 3.000.000).
- **Ligação com produtos:** pelos códigos impressos na imagem, lidos por OCR e comparados com `produto.codigo_pesq`.
  Código só com números só vale se o tipo de peça do título bater com o produto.
- Correções manuais no topo do `informativos.py`: `TITULO_CORRIGIDO`, `CODIGOS_EXTRAS`, `CODIGOS_IGNORAR`.
- Sem produto hoje: MMC020 da Cofap (JHC55004) e 9 da Magneti Marelli (bobinas, sensores, compressor...). Os códigos
  citados não existem nas bases instaladas; a da Magneti Marelli é de 21/05/2026.

## Estrutura do banco
- `linha`, `arvore` — linhas e árvores Sistema (1) > Grupo (2) > Subgrupo (3). Algumas folhas estão no nível 2
- `produto` — `marca` (Cofap / Magneti Marelli), `base` de origem e `grupo_cofap` (grupo do catálogo de origem);
  `produto_linha` e `produto_arvore` ligam o produto às linhas e subgrupos
- `regra_classificacao` — regras usadas (`base`: cofap, MM, MOTO; `grupo_regex` nas regras das marcas)
- `aplicacao` + `produto_aplicacao` — veículos; `referencia_cruzada` — códigos equivalentes de outras marcas
- `fabricante` — montadoras e marcas (as que só existem nas bases novas têm id a partir de 10000); `distribuidor` — rede Cofap
- `informativo` (`marca`, `base`) e `informativo_produto`
- `origem` — `base_<id>` = nome | data de emissão | versão de cada base
- `v_produto_sem_classificacao`, `v_informativo_sem_produto` — pendências para revisar

## Usar no Access
- **Importar:** rode `python scripts\exportar_csv.py catalogo_sistema.db csv_access` para atualizar os CSVs e, no Access,
  Dados Externos > Novo Arquivo de Texto > cada CSV (delimitado por `;`, primeira linha com nomes, UTF-8). Crie as relações pelos campos `*_id`.
- **Vincular ao vivo:** instale o driver SQLite ODBC (http://www.ch-werner.de/sqliteodbc/), crie uma DSN para
  `catalogo_sistema.db` e use Dados Externos > ODBC > Vincular.
