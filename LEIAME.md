# Catálogo de peças Cofap

Página única (`index.html`), sem servidor. O banco SQLite vai embutido em `lib/catalogo_db.js` e abre sozinho,
tanto com duplo clique no arquivo quanto publicado no GitHub Pages.

## Como usar
1. Abra o `index.html` no Chrome ou Edge (ou o endereço publicado). O catálogo carrega sozinho.
   Se `lib/catalogo_db.js` não existir, a página pede o `catalogo_sistema.db` (botão ou arrastar).
2. Escolha a linha nas abas (Passeio, Caminhão, Ônibus, Trator, Moto), navegue pela árvore Sistema > Grupo > Subgrupo,
   filtre por montadora/modelo e busque por código Cofap, código de concorrente (Nakata, Monroe, KYB...) ou texto.
3. **Informativos** (botão no cabeçalho): lançamentos técnicos da Cofap, com filtro por categoria, ano e mês e busca
   por título, número (MMC001), código de produto ou veículo. Cada informativo lista os produtos citados; clicar num
   produto abre o detalhe dele no catálogo. No detalhe do produto aparece a seção **Informativos técnicos**.

As fotos dos produtos ficam em `FotoProd/` (JPG, nomes em minúsculas) e as dos informativos em `Informativos/`.
A única dependência externa é a fonte Barlow (Google Fonts), com fallback automático.

## Conteúdo
| Arquivo | Função |
|---|---|
| `index.html` + `lib/` | Interface (sql.js embutido, lê o banco direto no navegador) |
| `lib/catalogo_db.js` | Banco embutido em base64 — carregado como `catalogo_db.js?v=AAAAMMDD` |
| `catalogo_sistema.db` | Banco SQLite com produtos, árvores, aplicações, referências, classificação e informativos |
| `FotoProd/` | Fotos dos produtos |
| `Informativos/<código>.jpg` | Imagens dos informativos técnicos (680 × 945 px) |
| `Informativos/mini/<código>.jpg` | Miniaturas usadas na lista |
| `scripts/gerar_banco.py` | Recria o banco a partir do `CatalogoExpresso.c01` e das árvores `.xlsx` |
| `scripts/informativos.py` | Converte os informativos, lê os códigos por OCR e grava as tabelas de informativos |
| `scripts/informativos_ocr.json` | Cache do OCR (não apague: evita precisar do Tesseract para os informativos já lidos) |
| `scripts/recuperar_fotos.py`, `embutir_banco.py`, `exportar_csv.py` | Fotos, banco embutido e exportação CSV |
| `csv_access/` | CSVs para importar no Access |

## Atualizar o catálogo (nova versão do Catálogo Expresso)
Na pasta `catalogo`, com o programa da Cofap atualizado em `C:\ProgramData\CatalogoProdutosCofap`:

```
python scripts\gerar_banco.py C:\ProgramData\CatalogoProdutosCofap\Configuracoes\CatalogoExpresso.c01 pasta_das_arvores catalogo_sistema.db
python scripts\informativos.py C:\ProgramData\CatalogoProdutosCofap\Configuracoes\CatalogoExpresso.c01 C:\ProgramData\CatalogoProdutosCofap\Informativos catalogo_sistema.db
```

A ordem importa: o `gerar_banco.py` recria o banco do zero e o `informativos.py` acrescenta os informativos,
regrava `lib/catalogo_db.js` e troca o `?v=` no `index.html` (data de hoje; se já estiver com a data de hoje,
vira `AAAAMMDDb`, `c`...). Sem trocar o `?v=` o navegador pode mostrar o banco antigo do cache.

Requisitos: Python 3.9+, `numpy`, `openpyxl`, `Pillow`. O **Tesseract OCR** só é necessário quando vierem informativos
novos (instalador para Windows: https://github.com/UB-Mannheim/tesseract/wiki; o script procura em
`C:\Program Files\Tesseract-OCR`). Sem ele, o script usa o cache e avisa quais informativos ficaram sem leitura.

## Informativos técnicos
- Origem: tabela `INFORMATIVO` do `.c01` + arquivos `.img` de `C:\ProgramData\CatalogoProdutosCofap\Informativos`.
- Os `.img` são **JPEG comuns, sem cifra** (diferente das fotos `#C3p:`). O script só confere a assinatura e copia como `.jpg`.
- Todos são panfletos públicos "Lançamento de Produto" (MMC001 em diante), com o site mmcofap.com.br no rodapé.
- `CategoriaInformativo` vem vazia na origem; a categoria é o começo do título ("Amortecedor - Ford" → Amortecedor)
  e as montadoras são o resto.
- **Ligação com produtos:** pelos códigos Cofap impressos na imagem. O OCR roda duas vezes (página inteira e ampliada 3×)
  e cada trecho parecido com código é comparado com `produto.codigo_pesq`, corrigindo trocas comuns (O→0, I→1).
  Código só com números (ex.: 45913) só vale se o tipo de peça do título bater com a descrição do produto.
- Correções manuais ficam no topo do `informativos.py`: `TITULO_CORRIGIDO` (o 1205 vem como "Amortecedor" mas é mola a gás),
  `CODIGOS_EXTRAS` e `CODIGOS_IGNORAR`.
- Situação atual: 187 informativos, 303 ligações com 298 produtos. Só o MMC020 (JHC55004) ficou sem produto:
  o código não existe no catálogo atual.

## Estrutura do banco
- `linha` — Passeio, Caminhão, Ônibus, Trator, Moto
- `arvore` — Sistema (nível 1) > Grupo (2) > Subgrupo (3), por linha
- `produto` — itens Cofap; `produto_linha` e `produto_arvore` ligam cada produto às linhas e subgrupos
- `regra_classificacao` — regras usadas na ligação (descrição + posição → subgrupo)
- `aplicacao` + `produto_aplicacao` — veículos em que cada peça serve
- `referencia_cruzada` — códigos equivalentes de outras marcas
- `fabricante` — montadoras e marcas; `distribuidor` — rede de distribuidores
- `informativo` — número, data, título, categoria, montadoras, caminho da imagem, texto do OCR
- `informativo_produto` — informativo × produto (`codigo_lido`, `confere_tipo`, `origem` = ocr/manual)
- `v_produto_sem_classificacao`, `v_informativo_sem_produto` — pendências para revisar

## Usar no Access
- **Importar:** rode `python scripts\exportar_csv.py catalogo_sistema.db csv_access` e, no Access, Dados Externos >
  Novo Arquivo de Texto > cada CSV (delimitado por `;`, primeira linha com nomes, UTF-8). Crie as relações pelos campos `*_id`.
- **Vincular ao vivo:** instale o driver SQLite ODBC (http://www.ch-werner.de/sqliteodbc/), crie uma DSN para
  `catalogo_sistema.db` e use Dados Externos > ODBC > Vincular.
