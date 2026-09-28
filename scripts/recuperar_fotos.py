"""Recupera as fotos do Catálogo Cofap (pasta FotoProd) para JPG normal.

As fotos do Catálogo Expresso não são JPG comuns:
    "#C3p:112048" + 112 bytes cifrados + miolo do JPG em claro + 48 bytes cifrados
Os 112 bytes cifrados são o cabeçalho (SOI, APP0 e tabelas de quantização) e os 48 finais
são o fim dos dados da imagem. A chave não está nos arquivos, então o script RECONSTRÓI:
  - cabeçalho: as tabelas de quantização são recalculadas a partir dos 58 valores da
    tabela de crominância que ficaram em claro (tabelas padrão IJG, fator conferido valor a valor);
  - final: os 46 bytes de dados perdidos são preenchidos repetindo o padrão do fundo
    (normalmente branco) e o marcador de fim FFD9 é recolocado.
Resultado: a imagem abre em qualquer programa. Nos poucos casos em que o canto inferior
direito não é fundo liso, pode aparecer um pequeno defeito nessa região.

Uso:
    python recuperar_fotos.py pasta_origem/FotoProd pasta_destino/FotoProd
Os arquivos de saída ficam com o nome em minúsculas. Requer Python 3.
Recomendado: pip install pillow  (valida cada foto e corrige a faixa lisa que pode sobrar no
canto inferior; sem Pillow as fotos abrem normalmente, só sem esse retoque).
"""
import os
import struct
import sys

ASSINATURA = b"#C3p:"
ZZ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14,
      21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60,
      61, 54, 47, 55, 62, 63]
LUM = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29,
       51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121,
       120, 101, 72, 92, 95, 98, 112, 100, 103, 99]
CHR = [17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99, 24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99,
       99, 99, 99, 99] + [99] * 32


def tabela(padrao, s):
    return bytes(min(255, max(1, (padrao[ZZ[i]] * s + 50) // 100)) for i in range(64))


def fator_escala(visiveis, inicio):
    """Acha o fator IJG que reproduz os valores da tabela que ficaram em claro."""
    for s in range(1, 5001):
        if tabela(CHR, s)[inicio:inicio + len(visiveis)] == visiveis:
            return s
    return None


def padrao_fundo(dados):
    """Padrão periódico mais longo do trecho de imagem (normalmente o fundo branco)."""
    melhor, tam = b"", 0
    for p in range(1, 33):
        run = 0
        for i in range(len(dados) - p):
            if dados[i] == dados[i + p]:
                run += 1
                if run >= p and run > tam:
                    bloco = dados[i + 1 - p:i + 1]
                    if b"\xff" not in bloco:
                        melhor, tam = bloco, run
            else:
                run = 0
    return melhor


def completar_final(dados, faltam):
    """Preenche os bytes perdidos com o padrão do fundo (primeiro o do final, senão o mais frequente)."""
    for p in range(1, 33):
        bloco = dados[-p:]
        if dados[-3 * p:] == bloco * 3 and b"\xff" not in bloco:
            break
    else:
        bloco = padrao_fundo(dados)
    if not bloco:
        return b""  # sem padrão: só encerra a imagem
    return (bloco * (faltam // len(bloco) + 1))[:faltam]


def recuperar(orig: bytes) -> bytes:
    if not orig.startswith(ASSINATURA):
        return orig  # já é uma imagem comum
    cab = int(orig[5:8])     # 112
    fim = int(orig[8:11])    # 48
    corpo = orig[11 + cab:len(orig) - fim]
    # corpo começa no meio da tabela de crominância e vai até antes do SOF (FFC0/FFC2)
    sof = min(i for i in (corpo.find(b"\xff\xc0"), corpo.find(b"\xff\xc2")) if i >= 0)
    visiveis = corpo[:sof]
    inicio = 64 - len(visiveis)
    s = fator_escala(visiveis, inicio)
    if s is None:
        raise ValueError("tabela de quantização fora do padrão")
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    dqt = (b"\xff\xdb\x00\x43\x00" + tabela(LUM, s) + b"\xff\xdb\x00\x43\x01" + tabela(CHR, s))
    miolo = corpo[sof:]
    sos = miolo.find(b"\xff\xda")
    dados_img = miolo[sos + 2 + struct.unpack('>H', miolo[sos + 2:sos + 4])[0]:]
    return b"\xff\xd8" + app0 + dqt + miolo + completar_final(dados_img, fim - 2) + b"\xff\xd9"


def tamanho_mcu(jpg):
    """Largura/altura do MCU a partir do SOF (8 para 4:4:4, 16 para 4:2:0)."""
    i = jpg.find(b"\xff\xc0")
    if i < 0:
        i = jpg.find(b"\xff\xc2")
    amostra = jpg[i + 11]  # fatores do componente Y
    return 8 * (amostra >> 4), 8 * (amostra & 15)


def limpar_final(caminho, Image, mcu):
    """Os últimos blocos preenchidos saem num tom liso diferente do fundo; repinta-os com a cor do fundo."""
    im = Image.open(caminho)
    im.load()
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    fundo = px[0, 0]
    bw, bh = mcu
    cols, lins = -(-w // bw), -(-h // bh)
    mudou = False
    for n in range(cols * lins - 1, -1, -1):
        x0, y0 = (n % cols) * bw, (n // cols) * bh
        caixa = (x0, y0, min(w, x0 + bw), min(h, y0 + bh))
        faixa = rgb.crop(caixa).getextrema()
        liso = all(b - a <= 6 for a, b in faixa)
        cor = tuple((a + b) // 2 for a, b in faixa)
        if not liso or min(cor) < 170:
            break
        if max(abs(c - f) for c, f in zip(cor, fundo)) > 3:
            rgb.paste(fundo, caixa)
            mudou = True
    if mudou:
        rgb.save(caminho, "JPEG", quality=92)


def main(origem, destino):
    os.makedirs(destino, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        Image = None
    ok = falhas = 0
    for nome in sorted(os.listdir(origem)):
        if not nome.lower().endswith((".jpg", ".jpeg")):
            continue
        caminho = os.path.join(origem, nome)
        try:
            dados = recuperar(open(caminho, "rb").read())
            saida = os.path.join(destino, nome.lower())
            open(saida, "wb").write(dados)
            if Image:
                limpar_final(saida, Image, tamanho_mcu(dados))
            ok += 1
        except Exception as e:
            falhas += 1
            print(f"Falha em {nome}: {e}")
    print(f"{ok} fotos recuperadas, {falhas} falhas -> {destino}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
