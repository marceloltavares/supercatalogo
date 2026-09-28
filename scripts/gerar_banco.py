"""
Gera o catalogo_sistema.db a partir dos catálogos do programa Catálogo Expresso (Ideia 2001)
instalados em C:\\ProgramData e das árvores .xlsx (Passeio, Caminhão, Ônibus, Trator, Moto).

Uso (na pasta catalogo):
  python scripts\\gerar_banco.py
  python scripts\\gerar_banco.py --origem C:\\ProgramData --arvores arvores --saida catalogo_sistema.db
  python scripts\\gerar_banco.py --bases cofap,pesada          (só algumas bases)

Depois rode o scripts\\informativos.py (informativos + banco embutido + ?v= do index.html)
e o scripts\\recuperar_fotos.py para as fotos novas. O atualizar_catalogo.py faz tudo em sequência.

Bases (lista BASES abaixo):
  cofap   Catálogo Cofap (base principal)
  pesada  Cofap Amortecedores Linha Pesada: mesclada na Cofap (só entra o que falta)
  mm      Magneti Marelli
  moto    Cofap Magneti Marelli Motocicletas (marca pelo código: ver regras_marcas.marca_moto)

Linha de cada aplicação (Passeio/Caminhão/Ônibus/Trator/Moto):
  1. base com linha fixa (moto = 5);
  2. tabela scripts\\linha_aplicacao.csv (decisões já tomadas; pode ser editada à mão);
  3. regras_marcas.LINHA_MONTADORA (montadoras que só existem nas bases novas);
  4. regra geral: palavras (ÔNIBUS, CAMINHÃO, TRATOR...), mesmo modelo, padrão do modelo
     e montadora, aprendidos da tabela; sem nada disso, Passeio.
  A tabela é regravada no fim com todas as aplicações e a origem da decisão.

Classificação na árvore:
  - produtos Cofap: REGRAS_COFAP (descrição + posição -> subgrupo, por linha);
  - Magneti Marelli e Motocicletas: regras_marcas.MM / MOTO (grupo do catálogo + descrição),
    com regras_marcas.EQUIVALENTES para Caminhão, Ônibus e Trator.

Requisitos: Python 3.9+, numpy, openpyxl
"""
import argparse
import csv
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict

import numpy as np
from openpyxl import load_workbook

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import regras_marcas as RM  # noqa: E402

PAGE = 8192
CSV_LINHAS = os.path.join(AQUI, "linha_aplicacao.csv")

LINHAS = [(1, "passeio", "Passeio", "Passeio.xlsx"), (2, "caminhao", "Caminhão", "Caminhão.xlsx"),
          (3, "onibus", "Ônibus", "Onibus.xlsx"), (4, "trator", "Trator", "Trator.xlsx"),
          (5, "moto", "Moto", "Moto.xlsx")]

# aplic: coluna da APLICACAO de cada base -> campo do banco
BASES = [
    dict(id="cofap", nome="Cofap", pasta="CatalogoProdutosCofap", marca="Cofap", modo="principal", offset=0,
         aplic=dict(complemento="ComplementoAplicacao", anos="ComplementoAplicacao2",
                    complemento3="ComplementoAplicacao3", complemento4="ComplementoAplicacao4")),
    dict(id="pesada", nome="Cofap Linha Pesada", pasta="CatalogoCofapAmortecedores-LinhaPesada", marca="Cofap",
         modo="mesclar", offset=3_000_000,
         aplic=dict(complemento="ComplementoAplicacao3_1", anos="ComplementoAplicacao3_2",
                    complemento3="ComplementoAplicacao3_3", complemento4="ComplementoAplicacao3_4")),
    dict(id="mm", nome="Magneti Marelli", pasta="CatalogoProdutosMagnetiMarelli", marca="Magneti Marelli",
         modo="marca", regras="MM", offset=1_000_000,
         aplic=dict(complemento="ComplementoAplicacao", anos="ComplementoAplicacao2",
                    complemento3="ComplementoAplicacao3")),
    dict(id="moto", nome="Cofap Magneti Marelli Motocicletas", pasta="CatalogoProdutosCofapMagnetiMarelliMotocicletas",
         marca=RM.marca_moto, modo="marca", regras="MOTO", linha=5, offset=2_000_000,
         aplic=dict(anos="ComplementoAplicacao3_1", complemento="ComplementoAplicacao3_2")),
]

# --------------------------------------------------------------------------
# Regras Cofap: (linha_id, descrição regex, posição regex, ["Grupo > Subgrupo", ...], observação)
# Descrição casa inteira (^...$); posição vazia = qualquer. A primeira que casar vale.
# --------------------------------------------------------------------------
REGRAS_COFAP = [
    (1, 'AMORTECEDOR', 'ESTICADOR', ['Correias e Polias > Polias e Tensionadores'], 'Amortecedor do tensionador'),
    (1, 'AMORTECEDOR', 'CAPÔ', ['Lataria > Capô'], ''),
    (1, 'AMORTECEDOR', 'TAMPA TRASEIRA|CAÇAMBA', ['Lataria > Tampa Traseira/Porta-malas'], ''),
    (1, 'AMORTECEDOR', 'BANCO', ['Acabamentos Internos > Bancos (e Componentes)'], ''),
    (1, 'AMORTECEDOR', 'DIREÇÃO', ['Sistema de Direção > Barras Axiais/Braços de Direção'], 'Amortecedor de direção'),
    (1, 'AMORTECEDOR', '^DIANT.*TRAS', ['Suspensão Dianteira > Amortecedores Dianteiros', 'Suspensão Traseira > Amortecedores Traseiros'], 'Serve nas duas posições'),
    (1, 'AMORTECEDOR', '^DIANT', ['Suspensão Dianteira > Amortecedores Dianteiros'], ''),
    (1, 'AMORTECEDOR', '^TRAS|EIXO TRASEIRO', ['Suspensão Traseira > Amortecedores Traseiros'], ''),
    (1, 'MOLA A GÁS', 'CAPÔ|TAMPA DO MOTOR|TAMPA DIANTEIRA|^DIANT', ['Lataria > Capô'], ''),
    (1, 'MOLA A GÁS', 'PORTA MALAS|TAMPA TRASEIRA|PORTA TRASEIRA|BAGAGEIRO|VIDRO DA TAMPA|^TRASEIRA$', ['Lataria > Tampa Traseira/Porta-malas'], ''),
    (1, 'MOLA A GÁS', 'GRADE', ['Para-choques e Grades > Grade Frontal'], ''),
    (1, 'MOLA A GÁS', 'BANCO|CAMA', ['Acabamentos Internos > Bancos (e Componentes)'], ''),
    (1, 'BANDEJA', 'DIANT', ['Suspensão Dianteira > Bandejas/Braços de Suspensão'], ''),
    (1, 'BANDEJA', 'TRAS', ['Suspensão Traseira > Braços de Suspensão Traseira (Multilink, etc.)'], ''),
    (1, 'BARRA DE DIREÇÃO|BRAÇO P.*MAN', '', ['Sistema de Direção > Barras Axiais/Braços de Direção'], ''),
    (1, 'BIELETA.*', '^DIANT.*TRAS', ['Suspensão Dianteira > Bieletas Dianteiras', 'Suspensão Traseira > Bieletas Traseiras'], ''),
    (1, 'BIELETA.*', 'DIANT', ['Suspensão Dianteira > Bieletas Dianteiras'], ''),
    (1, 'BIELETA.*', 'TRAS', ['Suspensão Traseira > Bieletas Traseiras'], ''),
    (1, 'KIT BARRA ESTABILIZADORA', 'DIANT', ['Suspensão Dianteira > Barra Estabilizadora Dianteira'], ''),
    (1, 'KIT BARRA ESTABILIZADORA', 'TRAS', ['Suspensão Traseira > Barra Estabilizadora Traseira'], ''),
    (1, 'BARRA DE TORÇÃO', '', ['Suspensão Traseira > Eixo de Torção/Eixo Rígido'], ''),
    (1, 'BUCHA', 'MOTOR', ['Coxins e Suportes do Motor > Coxins do Motor'], ''),
    (1, 'BUCHA', 'DIREÇÃO', ['Sistema de Direção > Caixa de Direção (Mecânica, Hidráulica, Elétrica)'], ''),
    (1, 'BUCHA', '^DIANT.*TRAS', ['Suspensão Dianteira > Buchas (Bandeja, Barra Estabilizadora)', 'Suspensão Traseira > Buchas Traseiras'], ''),
    (1, 'BUCHA', 'DIANT', ['Suspensão Dianteira > Buchas (Bandeja, Barra Estabilizadora)'], ''),
    (1, 'BUCHA', 'TRAS', ['Suspensão Traseira > Buchas Traseiras'], ''),
    (1, 'SUPORTE', 'MOTOR', ['Coxins e Suportes do Motor > Coxins do Motor'], ''),
    (1, 'SUPORTE', 'CÂMBIO', ['Coxins e Suportes da Transmissão > Coxins do Câmbio'], ''),
    (1, 'SUPORTE', 'DIANT', ['Suspensão Dianteira > Coxins e Batentes do Amortecedor'], 'Suporte/coxim do amortecedor'),
    (1, 'SUPORTE', 'TRAS', ['Suspensão Traseira > Buchas Traseiras'], 'Árvore não tem nó de coxim traseiro'),
    (1, 'RESTRITOR DE TORQUE', '', ['Coxins e Suportes do Motor > Coxins do Motor'], ''),
    (1, 'BATENTE|ISOLADOR|CALÇO|APOIO DE MOLA', '', ['Suspensão Dianteira > Coxins e Batentes do Amortecedor'], ''),
    (1, '(TOP )?KIT SUSPENSÃO', 'DIANT', ['Suspensão Dianteira > Coxins e Batentes do Amortecedor'], ''),
    (1, '(TOP )?KIT SUSPENSÃO', 'TRAS', ['Suspensão Traseira > Amortecedores Traseiros'], 'Kit batente/coifa traseiro; árvore não tem nó próprio'),
    (1, 'MOLA HELICOIDAL', 'DIANT', ['Suspensão Dianteira > Molas Helicoidais Dianteiras'], ''),
    (1, 'MOLA HELICOIDAL|FEIXE DE MOLA', 'TRAS', ['Suspensão Traseira > Molas Traseiras (Helicoidais, Feixe de Molas)'], ''),
    (1, 'CUBO DE RODA', '', ['Rodas e Pneus > Cubos de Roda'], ''),
    (1, 'PASTILHA PARA FREIO', '', ['Freio a Disco > Pastilhas de Freio'], ''),
    (1, 'PIVÔ DE SUSPENSÃO', '', ['Suspensão Dianteira > Pivôs de Suspensão'], ''),
    (1, 'TERMINAL AXIAL', '', ['Sistema de Direção > Barras Axiais/Braços de Direção'], ''),
    (1, 'TERMINAL DE DIREÇÃO', '', ['Sistema de Direção > Terminais de Direção'], ''),
    (1, 'SEMIEIXO', '', ['Eixos de Transmissão e Homocinéticas > Semieixos'], ''),
    (1, 'JUNTA HOMOCINÉTICA.*|KIT (DE )?REPARO.*|TRIZETA|TULIPA', '', ['Eixos de Transmissão e Homocinéticas > Juntas Homocinéticas (Fixa, Deslizante)'], ''),
    (2, 'AMORTECEDOR', 'CABINE', ['Suspensão da Cabine > Amortecedores da Cabine'], ''),
    (2, 'MOLA HELICOIDAL|FEIXE DE MOLA', 'CABINE', ['Suspensão da Cabine > Molas Helicoidais/Feixe de Molas'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'CABINE', ['Suspensão da Cabine > Bolsas de Ar da Cabine'], ''),
    (2, 'BUCHA|SUPORTE|BATENTE', 'CABINE', ['Suspensão da Cabine > Batentes e Buchas da Suspensão da Cabine'], ''),
    (2, 'MOLA A GÁS', 'CABINE|GRADE|CAPÔ|TAMPA DO MOTOR|TAMPA DIANTEIRA|^DIANT', ['Lataria e Componentes Externos > Capô/Grade Frontal'], ''),
    (2, 'MOLA A GÁS', 'DEFLETOR', ['Lataria e Componentes Externos > Defletores de Ar (Teto, Laterais)'], ''),
    (2, 'MOLA A GÁS', 'DEGRAU', ['Lataria e Componentes Externos > Estribos / Degraus de Acesso'], ''),
    (2, 'MOLA A GÁS', 'CAMA', ['Acabamentos Internos > Cama/Beliche (Cabine Leito)'], ''),
    (2, 'MOLA A GÁS|AMORTECEDOR|MOLA PNEUMÁTICA', 'BANCO', ['Acabamentos Internos > Banco do Motorista (Suspensão Pneumática/Mecânica, Ajustes)'], ''),
    (2, 'MOLA A GÁS', 'PORTA OBJETOS|BAGAGEIRO', ['Acabamentos Internos > Console Central/Porta-objetos'], ''),
    (2, 'MOLA A GÁS', 'ESTEPE', ['Acessórios Externos > Suporte de Estepe'], ''),
    (2, 'MOLA A GÁS', 'TANQUE|LATERAL DO MOTOR|CAIXA', ['Acessórios Externos > Caixa de Ferramentas/Cozinha'], 'Tampas laterais de caixa/tanque'),
    (2, 'AMORTECEDOR', '3º EIXO|EIXO AUXILIAR|EIXO INTERMEDIÁRIO', ['Suspensão do Eixo Auxiliar (Truck/3º Eixo) > Amortecedores'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'LEVANTE', ['Suspensão do Eixo Auxiliar (Truck/3º Eixo) > Mecanismo de Levantamento (Suspensor Pneumático)'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', '^EIXO DIANTEIRO / TRASEIRO / 3º', ['Suspensão Dianteira (Metálica/Pneumática) > Bolsas de Ar Dianteiras (Se pneumática)', 'Suspensão Traseira (Metálica/Pneumática) > Bolsas de Ar Traseiras (Foles)', 'Suspensão do Eixo Auxiliar (Truck/3º Eixo) > Bolsas de Ar/Molas'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', '3º EIXO', ['Suspensão do Eixo Auxiliar (Truck/3º Eixo) > Bolsas de Ar/Molas'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'DIANT.*TRAS', ['Suspensão Dianteira (Metálica/Pneumática) > Bolsas de Ar Dianteiras (Se pneumática)', 'Suspensão Traseira (Metálica/Pneumática) > Bolsas de Ar Traseiras (Foles)'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'DIANT', ['Suspensão Dianteira (Metálica/Pneumática) > Bolsas de Ar Dianteiras (Se pneumática)'], ''),
    (2, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'TRAS|TRAÇÃO|^EIXO$', ['Suspensão Traseira (Metálica/Pneumática) > Bolsas de Ar Traseiras (Foles)'], "Posição 'EIXO' sem lado = eixo traseiro"),
    (2, 'AMORTECEDOR', '^DIANT.*TRAS', ['Suspensão Dianteira (Metálica/Pneumática) > Amortecedores Dianteiros', 'Suspensão Traseira (Metálica/Pneumática) > Amortecedores Traseiros'], ''),
    (2, 'AMORTECEDOR', '^DIANT|EIXO DIRECIONAL', ['Suspensão Dianteira (Metálica/Pneumática) > Amortecedores Dianteiros'], ''),
    (2, 'AMORTECEDOR', '^TRAS|EIXO TRASEIRO|^EIXO$|SUSPENSÃO AR', ['Suspensão Traseira (Metálica/Pneumática) > Amortecedores Traseiros'], ''),
    (2, 'AMORTECEDOR', 'ESTICADOR', ['Correias e Polias > Tensionadores Automáticos/Manuais'], ''),
    (2, 'FEIXE DE MOLA', 'DIANT', ['Suspensão Dianteira (Metálica/Pneumática) > Feixe de Molas (Parabólicas/Trapezoidais)'], ''),
    (2, 'FEIXE DE MOLA', 'TRAS', ['Suspensão Traseira (Metálica/Pneumática) > Feixe de Molas (Principal, Auxiliar)'], ''),
    (2, 'BARRA DE TORÇÃO', '', ['Suspensão Traseira (Metálica/Pneumática) > Barras Tensoras / Braços de Controle (V-Stay, Torque Rods)'], ''),
    (2, 'KIT BARRA ESTABILIZADORA|BIELETA.*', 'DIANT', ['Suspensão Dianteira (Metálica/Pneumática) > Barra Estabilizadora Dianteira'], ''),
    (2, 'BATENTE|(TOP )?KIT SUSPENSÃO', 'TRAS', ['Suspensão Traseira (Metálica/Pneumática) > Batentes da Suspensão'], ''),
    (2, 'BATENTE|(TOP )?KIT SUSPENSÃO|ISOLADOR|CALÇO|APOIO DE MOLA', '', ['Suspensão Dianteira (Metálica/Pneumática) > Batentes da Suspensão'], ''),
    (2, 'PINO', 'SUSPENSÃO', ['Suspensão Dianteira (Metálica/Pneumática) > Pinos e Buchas (Jumelos, Suportes)'], ''),
    (2, 'BUCHA|SUPORTE', 'MOTOR', ['Coxins e Suportes do Motor > Coxins Hidráulicos/Borracha'], ''),
    (2, 'SUPORTE', 'CÂMBIO', ['Estrutura Principal do Chassi > Suportes de Fixação (Motor, Câmbio, Suspensão, Cabine, Tanques)'], ''),
    (2, 'BUCHA|SUPORTE', 'DIANT', ['Suspensão Dianteira (Metálica/Pneumática) > Pinos e Buchas (Jumelos, Suportes)'], ''),
    (2, 'BUCHA|SUPORTE', '', ['Estrutura Principal do Chassi > Suportes de Fixação (Motor, Câmbio, Suspensão, Cabine, Tanques)'], ''),
    (2, 'ROLETE', 'FREIO', ['Freio de Roda (Tambor/Disco) > Sapatas de Freio (Com Lonas)'], 'Rolete da sapata'),
    (2, 'PASTILHA PARA FREIO', '', ['Freio de Roda (Tambor/Disco) > Pastilhas de Freio'], ''),
    (2, 'CUBO DE RODA', 'TRAS', ['Cubos de Roda > Cubo Traseiro'], ''),
    (2, 'CUBO DE RODA', '', ['Cubos de Roda > Cubo Dianteiro'], ''),
    (2, 'TERMINAL AXIAL|TERMINAL DE DIREÇÃO', '', ['Barras e Terminais > Terminais de Direção (Axiais, Esféricos)'], ''),
    (2, 'BARRA DE DIREÇÃO', '', ['Barras e Terminais > Barra Longa (Conexão Caixa-Roda)'], ''),
    (2, 'BRAÇO P.*MAN', '', ['Componentes de Acionamento > Braço Pitman'], ''),
    (2, 'SEMIEIXO', '', ['Eixos de Tração > Semieixos'], ''),
    (3, 'AMORTECEDOR', '3º EIXO|EIXO AUXILIAR|EIXO INTERMEDIÁRIO', ['Suspensão do Eixo Auxiliar (3º eixo) > Amortecedores do 3º Eixo'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'LEVANTE', ['Suspensão do Eixo Auxiliar (3º eixo) > Mecanismo de Levantamento do Eixo'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', '^EIXO DIANTEIRO / TRASEIRO / 3º', ['Suspensão Dianteira > Bolsas de Ar Dianteiras (Foles)', 'Suspensão Traseira > Bolsas de Ar Traseiras (Foles)', 'Suspensão do Eixo Auxiliar (3º eixo) > Bolsas de Ar do 3º Eixo'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', '3º EIXO', ['Suspensão do Eixo Auxiliar (3º eixo) > Bolsas de Ar do 3º Eixo'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'DIANT.*TRAS', ['Suspensão Dianteira > Bolsas de Ar Dianteiras (Foles)', 'Suspensão Traseira > Bolsas de Ar Traseiras (Foles)'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'DIANT', ['Suspensão Dianteira > Bolsas de Ar Dianteiras (Foles)'], ''),
    (3, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|KIT PNEUMÁTICO', 'TRAS|TRAÇÃO|^EIXO$', ['Suspensão Traseira > Bolsas de Ar Traseiras (Foles)'], ''),
    (3, 'MOLA PNEUMÁTICA|AMORTECEDOR|MOLA A GÁS', 'BANCO', ['Acabamento Interno > Banco do Motorista (Com Suspensão Pneumática/Mecânica)'], ''),
    (3, 'AMORTECEDOR', '^DIANT.*TRAS', ['Suspensão Dianteira > Amortecedores Dianteiros', 'Suspensão Traseira > Amortecedores Traseiros'], ''),
    (3, 'AMORTECEDOR', '^DIANT|EIXO DIRECIONAL', ['Suspensão Dianteira > Amortecedores Dianteiros'], ''),
    (3, 'AMORTECEDOR', '^TRAS|EIXO TRASEIRO|^EIXO$|SUSPENSÃO AR', ['Suspensão Traseira > Amortecedores Traseiros'], ''),
    (3, 'MOLA A GÁS', 'PANTOGR|PORTA', ['Portas de Serviço e Acesso > Folhas de Porta (Urbanas/Rodoviárias/Pantográficas)'], ''),
    (3, 'MOLA A GÁS', 'BAGAGEIRO|CAIXA|TANQUE|LATERAL|CARROCERIA|GRADE', ['Revestimento Externo > Tampas de Bagageiro/Portinholas de Inspeção'], 'Carroceria/grade de ônibus = tampas e portinholas de acesso'),
    (3, 'AMORTECEDOR', 'ESTICADOR', ['Correias e Polias > Tensionadores Automáticos / Manuais'], ''),
    (3, 'MOLA A GÁS', 'TAMPA TRASEIRA|TAMPA DO MOTOR|^TRASEIRA|PORTA MALAS', ['Revestimento Externo > Painel Traseiro (Tampa - Fibra/Plástico)'], 'Tampa do motor traseiro'),
    (3, 'FEIXE DE MOLA', 'DIANT', ['Suspensão Dianteira > Feixe de Molas (Se aplicável)'], ''),
    (3, 'KIT BARRA ESTABILIZADORA|BIELETA.*', 'DIANT', ['Suspensão Dianteira > Barra Estabilizadora Dianteira'], ''),
    (3, 'BARRA DE TORÇÃO', '', ['Suspensão Traseira > Barras Tensoras Superiores/Inferiores (Braços)'], ''),
    (3, 'BATENTE|(TOP )?KIT SUSPENSÃO', 'TRAS', ['Suspensão Traseira > Batentes da Suspensão Traseira'], ''),
    (3, 'BATENTE|(TOP )?KIT SUSPENSÃO|ISOLADOR|CALÇO|APOIO DE MOLA', '', ['Suspensão Dianteira > Batentes da Suspensão Dianteira'], ''),
    (3, 'BUCHA|SUPORTE', 'MOTOR', ['Coxins e Suportes do Motor > Coxins Hidráulicos/Borracha'], ''),
    (3, 'BUCHA|SUPORTE|PINO', 'TRAS', ['Suspensão Traseira > Pinos e Buchas da Suspensão Traseira'], ''),
    (3, 'BUCHA|SUPORTE|PINO', 'DIANT', ['Suspensão Dianteira > Pinos e Buchas da Suspensão Dianteira'], ''),
    (3, 'BUCHA|SUPORTE', '', ['Estrutura Principal do Chassi > Suportes de Fixação (Motor, Câmbio, Suspensão)'], ''),
    (3, 'ROLETE', 'FREIO', ['Freio de Roda (Tambor/Disco) > Sapatas de Freio (Com Lonas)'], 'Rolete da sapata'),
    (3, 'PASTILHA PARA FREIO', '', ['Freio de Roda (Tambor/Disco) > Pastilhas de Freio'], ''),
    (3, 'CUBO DE RODA', 'TRAS', ['Cubos de Roda > Cubo Traseiro'], ''),
    (3, 'CUBO DE RODA', '', ['Cubos de Roda > Cubo Dianteiro'], ''),
    (3, 'SEMIEIXO', '', ['Eixo de Tração Traseiro / Central (Articulado) > Semieixos'], ''),
    (4, 'MOLA PNEUMÁTICA|BOLSA PNEUMÁTICA|AMORTECEDOR', 'DIANT', ['Eixo Dianteiro > Eixo com Suspensão (Independente/Barra única)'], 'Árvore não tem nó de suspensão traseira'),
    (4, 'MOLA A GÁS|AMORTECEDOR', 'BANCO', ['Assento e Comandos > Suspensão do Assento (Mecânica / Pneumática)'], ''),
    (4, 'PASTILHA PARA FREIO', '', ['Freio de Serviço (Eixo Traseiro) > Pastilhas / Placas de Fricção'], ''),
    (4, 'TERMINAL AXIAL|TERMINAL DE DIREÇÃO', '', ['Componentes Mecânicos da Direção > Terminais de Direção (Axiais/Esféricos)'], ''),
    (4, 'CUBO DE RODA', 'TRAS', ['Cubos e Fixação > Cubo de Roda Traseiro'], ''),
    (4, 'CUBO DE RODA', '', ['Cubos e Fixação > Cubo de Roda Dianteiro'], ''),
    (4, 'PIVÔ DE SUSPENSÃO', '', ['Eixo Dianteiro > Pivôs de Direção (Superior/Inferior)'], ''),
    (5, 'AMORTECEDOR', 'TRAS', ['Suspensão Traseira > Amortecedor Convencional (Duplo-choque)'], ''),
    (5, 'PASTILHA PARA FREIO', 'DIANT', ['Freio Dianteiro > Pastilha de Freio (Orgânica/Metálica/Sinterizada)'], ''),
    (5, 'PASTILHA PARA FREIO', 'TRAS', ['Freio Traseiro > Pastilhas de Freio'], ''),
]

# --------------------------------------------------------------------------
def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


def chave_txt(s):
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def decifrar(caminho_c01: str) -> bytes:
    """.c01 = SQLite com páginas de 8192 bytes em XOR com um keystream fixo (tirado de uma página vazia)."""
    raw = open(caminho_c01, "rb").read()
    pages = np.frombuffer(raw, np.uint8).reshape(-1, PAGE)
    vazia = Counter(p.tobytes() for p in pages[1:]).most_common(1)[0][0]
    plano = np.zeros(PAGE, np.uint8)
    plano[0], plano[5] = 0x0D, 0x20
    chave = np.frombuffer(vazia, np.uint8) ^ plano
    dec = (pages ^ chave).tobytes()
    if dec[:16] != b"SQLite format 3\x00":
        raise SystemExit(f"Não foi possível decifrar {caminho_c01}")
    return dec


def nocase(a, b):
    a, b = a.lower(), b.lower()
    return (a > b) - (a < b)


def abrir_base(caminho_c01, tmp):
    p = os.path.join(tmp, os.path.basename(os.path.dirname(os.path.dirname(caminho_c01))) + ".db")
    open(p, "wb").write(decifrar(caminho_c01))
    c = sqlite3.connect(p)
    c.create_collation("NO_CASE_2", nocase)
    return c


def colunas(c, tabela):
    return [r[1] for r in c.execute(f"PRAGMA table_info({tabela})")]


# --------------------------------------------------------------------------
# Árvores
# --------------------------------------------------------------------------
CABECALHO = {"HIERARQUIA PROPOSTA:", "SISTEMA", "SISTEMAS"}


def ler_arvore(caminho_xlsx):
    ws = load_workbook(caminho_xlsx, read_only=True, data_only=True).worksheets[0]
    nos, idx = [], {}
    sistema = grupo = None

    def add(nome, pai, nivel):
        k = (pai, nome)
        if k in idx:
            return idx[k]
        caminho = nome if pai is None else f"{nos[pai]['caminho']} > {nome}"
        nos.append(dict(pai=pai, nivel=nivel, nome=nome, caminho=caminho))
        idx[k] = len(nos) - 1
        return idx[k]

    for linha in ws.iter_rows(values_only=True):
        s, g, sg = [(str(v).strip() if v is not None and str(v).strip() else None) for v in (list(linha) + [None] * 3)[:3]]
        if s and s.upper() in CABECALHO:
            continue
        if s:
            sistema = add(s, None, 1)
        if g and sistema is not None:
            grupo = add(g, sistema, 2)
        if sg and grupo is not None:
            add(sg, grupo, 3)
    return nos


# --------------------------------------------------------------------------
# Linha das aplicações
# --------------------------------------------------------------------------
PALAVRAS = [(3, r"\bONIBUS\b|MICRO-?ONIBUS|\bBRT\b|ARTICULADO|ENCARROC"),
            (2, r"\bCAMINH(AO|OES)\b|\bCAVALO MECANICO\b|\bCARRETA\b"),
            (4, r"\bTRATOR|COLHEITADEIRA|\bAGRICOLA|RETROESCAVADEIRA|ESCAVADEIRA|MOTONIVELADORA|EMPILHADEIRA")]


def assinatura(modelo):
    return re.sub(r"\s+", " ", re.sub(r"\d+(\.\d+)?", "9", sem_acento(modelo))).strip()


class Linhas:
    def __init__(self, caminho_csv):
        self.tabela, self.mm, self.ms, self.m = {}, defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
        self.fixa = {sem_acento(n): l for l, nomes in RM.LINHA_MONTADORA.items() for n in nomes}
        if os.path.exists(caminho_csv):
            with open(caminho_csv, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    l = int(r["linha"])
                    self.tabela[self.chave(r)] = l
                    mont = sem_acento(r["montadora"])
                    self.mm[(mont, sem_acento(r["modelo"]))][l] += 1
                    self.ms[(mont, assinatura(r["modelo"]))][l] += 1
                    self.m[mont][l] += 1
        self.saida = {}

    @staticmethod
    def chave(r):
        return tuple(chave_txt(r.get(k)) for k in ("montadora", "modelo", "complemento", "anos", "complemento3", "complemento4"))

    def decidir(self, r, fixa=None):
        k = self.chave(r)
        if fixa:
            l, como = fixa, "base"
        elif k in self.tabela:
            l, como = self.tabela[k], "tabela"
        else:
            mont = sem_acento(r.get("montadora"))
            txt = sem_acento(" ".join(r.get(x) or "" for x in ("modelo", "complemento", "anos", "complemento3", "complemento4")))
            l = como = None
            for lp, rx in PALAVRAS:
                if re.search(rx, txt):
                    l, como = lp, "palavra"
                    break
            if l is None and mont in self.fixa:
                l, como = self.fixa[mont], "montadora (lista)"
            if l is None:
                for d, kk, nome in ((self.mm, (mont, sem_acento(r.get("modelo"))), "modelo"),
                                    (self.ms, (mont, assinatura(r.get("modelo"))), "padrão do modelo"),
                                    (self.m, mont, "montadora")):
                    if kk in d:
                        l, como = d[kk].most_common(1)[0][0], nome
                        break
            if l is None:
                l, como = 1, "padrão"
        self.saida.setdefault(k, (l, como))
        return l

    def gravar(self, caminho_csv):
        with open(caminho_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["montadora", "modelo", "complemento", "anos", "complemento3", "complemento4", "linha", "decisao"])
            todas = {k: (l, "tabela") for k, l in self.tabela.items()}
            todas.update(self.saida)
            for k, (l, como) in sorted(todas.items()):
                w.writerow([*k, l, como])


# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE origem(chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE linha(id INTEGER PRIMARY KEY, codigo TEXT, nome TEXT, arquivo TEXT);
CREATE TABLE arvore(id INTEGER PRIMARY KEY, linha_id INTEGER REFERENCES linha(id), pai_id INTEGER REFERENCES arvore(id),
                    nivel INTEGER, nome TEXT, caminho TEXT, ordem INTEGER);
CREATE TABLE fabricante(id INTEGER PRIMARY KEY, nome TEXT, e_marca_peca INTEGER, e_montadora INTEGER);
CREATE TABLE produto(id INTEGER PRIMARY KEY, codigo TEXT, codigo_pesq TEXT, descricao TEXT,
                     grupo_cofap TEXT, linha_cofap TEXT, posicao TEXT, unidade TEXT,
                     foto TEXT, foto2 TEXT, foto3 TEXT, observacao TEXT, texto_busca TEXT,
                     marca TEXT, base TEXT);
CREATE TABLE aplicacao(id INTEGER PRIMARY KEY, montadora_id INTEGER REFERENCES fabricante(id),
                       linha_id INTEGER REFERENCES linha(id),
                       modelo TEXT, complemento TEXT, anos TEXT, complemento3 TEXT, complemento4 TEXT);
CREATE TABLE produto_aplicacao(produto_id INTEGER REFERENCES produto(id),
                               aplicacao_id INTEGER REFERENCES aplicacao(id),
                               PRIMARY KEY(produto_id, aplicacao_id));
CREATE TABLE produto_linha(produto_id INTEGER REFERENCES produto(id), linha_id INTEGER REFERENCES linha(id),
                           PRIMARY KEY(produto_id, linha_id));
CREATE TABLE referencia_cruzada(id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produto(id),
                                marca_id INTEGER REFERENCES fabricante(id), codigo TEXT, codigo_pesq TEXT);
CREATE TABLE regra_classificacao(id INTEGER PRIMARY KEY, linha_id INTEGER REFERENCES linha(id),
                                 descricao_regex TEXT, posicao_regex TEXT, destinos TEXT, observacao TEXT,
                                 base TEXT, grupo_regex TEXT);
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
CREATE INDEX ix_prod_marca ON produto(marca);
CREATE VIEW v_produto_sem_classificacao AS
  SELECT l.nome AS linha, p.* FROM produto_linha pl JOIN produto p ON p.id = pl.produto_id JOIN linha l ON l.id = pl.linha_id
  WHERE NOT EXISTS (SELECT 1 FROM produto_arvore pa JOIN arvore a ON a.id = pa.arvore_id
                    WHERE pa.produto_id = p.id AND a.linha_id = pl.linha_id);
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", default=r"C:\ProgramData", help="pasta onde estão os catálogos instalados")
    ap.add_argument("--arvores", default=os.path.join(RAIZ, "arvores"))
    ap.add_argument("--saida", default=os.path.join(RAIZ, "catalogo_sistema.db"))
    ap.add_argument("--bases", default=",".join(b["id"] for b in BASES), help="ids separados por vírgula")
    a = ap.parse_args()
    usar = [b for b in BASES if b["id"] in a.bases.split(",")]
    if not usar or usar[0]["id"] != "cofap":
        raise SystemExit("A base cofap precisa estar na lista (é a principal).")

    tmp = tempfile.mkdtemp()
    trabalho = os.path.join(tmp, "novo.db")
    db = sqlite3.connect(trabalho)
    db.executescript(SCHEMA)
    db.create_function("remove_acento", 1, sem_acento)
    L = Linhas(CSV_LINHAS)

    # ---------- linhas e árvores
    db.executemany("INSERT INTO linha VALUES(?,?,?,?)", LINHAS)
    folhas = {}   # (linha, caminho) -> id  (só nós sem filhos)
    nid = 0
    for lid, _, nome, arq in LINHAS:
        nos = ler_arvore(os.path.join(a.arvores, arq))
        base_id = nid
        for i, n in enumerate(nos):
            nid += 1
            db.execute("INSERT INTO arvore VALUES(?,?,?,?,?,?,?)",
                       (nid, lid, None if n["pai"] is None else base_id + n["pai"] + 1, n["nivel"], n["nome"], n["caminho"], nid))
        tem_filho = {n["pai"] for n in nos}
        for i, n in enumerate(nos):
            if i not in tem_filho:
                folhas[(lid, n["caminho"])] = base_id + i + 1

    def resolver(lid, destino):
        """'Grupo > Subgrupo' (fim do caminho) ou caminho completo -> id da folha."""
        if (lid, destino) in folhas:
            return folhas[(lid, destino)]
        ids = [i for (l, cam), i in folhas.items() if l == lid and cam.count(" > ") == 2 and cam.endswith(" > " + destino)]
        if len(ids) != 1:
            raise SystemExit(f"Destino não encontrado (ou ambíguo) na linha {lid}: {destino}")
        return ids[0]

    # ---------- bases
    fab_nome = {}          # nome sem acento -> id
    fab_flags = {}
    prod_chave = {}        # (marca, codigo_pesq) -> id
    prod_info = {}         # id -> (base, grupo, descricao, posicao)
    aplic_chave = {}       # chave texto -> id
    aplic_info = {}        # id -> (montadora_id, modelo sem acento)
    pa, refs_vistas = set(), set()
    origem = []

    for b in usar:
        c01 = os.path.join(a.origem, b["pasta"], "Configuracoes", "CatalogoExpresso.c01")
        src = abrir_base(c01, tmp)
        um = src.execute("SELECT DataEmissao, Versao, VersaoCatalogo FROM UMREGISTRO").fetchone()
        origem.append((b, um))
        off = b["offset"]

        # fabricantes (montadoras e marcas de referência)
        fmap = {}
        for fid, nome, fp, fa in src.execute("SELECT CodigoFabricante, DescricaoFabricante, FlagProduto, FlagAplicacao FROM FABRICANTE"):
            k = sem_acento(nome).strip()
            if b["modo"] == "principal":
                db.execute("INSERT INTO fabricante VALUES(?,?,?,?)", (fid, nome, fp, fa))
                fab_nome.setdefault(k, fid)
                fab_flags[fid] = [fp, fa]
                fmap[fid] = fid
                continue
            alvo = fab_nome.get(k) or fab_nome.get(re.sub(r"[^A-Z0-9]", "", k))
            if alvo is None:
                alvo = 10_000 + len(fab_flags)
                db.execute("INSERT INTO fabricante VALUES(?,?,?,?)", (alvo, nome, fp, fa))
                fab_nome[k] = alvo
                fab_nome.setdefault(re.sub(r"[^A-Z0-9]", "", k), alvo)
                fab_flags[alvo] = [fp, fa]
            else:
                fl = fab_flags[alvo]
                if (fp and not fl[0]) or (fa and not fl[1]):
                    fl[0], fl[1] = fl[0] or fp, fl[1] or fa
                    db.execute("UPDATE fabricante SET e_marca_peca=?, e_montadora=? WHERE id=?", (fl[0], fl[1], alvo))
            fmap[fid] = alvo
        fab_txt = {i: n for i, n in db.execute("SELECT id, nome FROM fabricante")}

        # produtos
        cp = colunas(src, "PRODUTO")
        aux = lambda n: n if n in cp else "NULL"
        grupos = dict(src.execute("SELECT CodigoGrupoProduto, DescricaoGrupoProduto FROM GRUPOPRODUTO"))
        obs = dict(src.execute("SELECT CodigoProduto, Observacao FROM PRODUTO_OBS"))
        pmap = {}
        for r in src.execute(f"""SELECT CodigoProduto, NumeroProduto, NumeroProdutoPesq, DescricaoProduto, CodigoGrupoProduto,
                                        {aux('CpoAuxProd1')}, {aux('CpoAuxProd2')}, Unidade, ArquivoFotoProduto,
                                        ArquivoFotoProduto2, ArquivoFotoProduto3, PCs FROM PRODUTO"""):
            pid, cod, pesq, desc, gid, lin, pos, un, f1, f2, f3, pcs = r
            grupo = grupos.get(gid)
            marca = b["marca"](cod, sem_acento(grupo)) if callable(b["marca"]) else b["marca"]
            k = (marca, (pesq or "").upper())
            if k in prod_chave:
                pmap[pid] = prod_chave[k]
                if b["modo"] == "mesclar" and obs.get(pid):
                    db.execute("UPDATE produto SET observacao = coalesce(observacao, ?) WHERE id = ?", (obs[pid], pmap[pid]))
                continue
            novo = pid + off
            db.execute("INSERT INTO produto VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (novo, cod, pesq, desc, grupo, lin, pos, un, f1, f2, f3, obs.get(pid), sem_acento(pcs), marca, b["id"]))
            prod_chave[k] = pmap[pid] = novo
            prod_info[novo] = (b, grupo, desc, pos)

        # aplicações
        ca = colunas(src, "APLICACAO")
        campos = ["complemento", "anos", "complemento3", "complemento4"]
        sel = ", ".join((b["aplic"].get(f) if b["aplic"].get(f) in ca else "NULL") for f in campos)
        amap, pendente = {}, {}
        for aid, fid, modelo, *vals in src.execute(f"SELECT CodigoAplicacao, CodigoFabricante, DescricaoAplicacao, {sel} FROM APLICACAO"):
            mid = fmap.get(fid)
            vals = [v or "" for v in vals]
            if b["modo"] != "principal":   # Magneti Marelli: "1.4 8V;Flex;MPI" -> "1.4 8V · Flex · MPI"
                vals = [" · ".join(x.strip() for x in v.split(";") if x.strip()) if ";" in v else v for v in vals]
            r = dict(montadora=fab_txt.get(mid, ""), modelo=modelo, **dict(zip(campos, vals)))
            k = Linhas.chave(r)
            if b["modo"] == "mesclar":
                # base mesclada: a aplicação só entra se o produto ainda não tiver esta montadora + modelo
                pendente[aid] = (k, r, mid, modelo)
                continue
            lid = L.decidir(r, b.get("linha"))
            novo = aid + off
            db.execute("INSERT INTO aplicacao VALUES(?,?,?,?,?,?,?,?)",
                       (novo, mid, lid, modelo, r["complemento"], r["anos"], r["complemento3"], r["complemento4"]))
            if b["modo"] == "principal":
                aplic_chave.setdefault(k, novo)
            aplic_info[novo] = (mid, sem_acento(modelo).strip())
            amap[aid] = novo
        if pendente:
            tem = {(p, *aplic_info[a_]) for p, a_ in pa}
        for p, ap_ in src.execute("SELECT CodigoProduto, CodigoAplicacao FROM PRODUTO_APLICACAO"):
            if p not in pmap:
                continue
            if ap_ in pendente:
                k, r, mid, modelo = pendente[ap_]
                if (pmap[p], mid, sem_acento(modelo).strip()) in tem:
                    continue
                if ap_ not in amap:
                    if k in aplic_chave:
                        amap[ap_] = aplic_chave[k]
                    else:
                        novo = ap_ + off
                        db.execute("INSERT INTO aplicacao VALUES(?,?,?,?,?,?,?,?)",
                                   (novo, mid, L.decidir(r, b.get("linha")), modelo, r["complemento"], r["anos"],
                                    r["complemento3"], r["complemento4"]))
                        aplic_info[novo] = (mid, sem_acento(modelo).strip())
                        amap[ap_] = novo
            if ap_ in amap:
                pa.add((pmap[p], amap[ap_]))

        # referências cruzadas
        for rid, p, fid, num, pesq in src.execute(
                "SELECT CodigoReferenciaCruzada, CodigoProduto, CodigoFabricante, NumeroProduto, NumeroProdutoPesq FROM REFERENCIACRUZADA"):
            if p not in pmap:
                continue
            k = (pmap[p], fmap.get(fid), (pesq or "").upper())
            if k in refs_vistas:
                continue
            refs_vistas.add(k)
            db.execute("INSERT INTO referencia_cruzada VALUES(?,?,?,?,?)", (rid + off, pmap[p], fmap.get(fid), num, pesq))

        if b["modo"] == "principal":
            tabs = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            if "DISTRIBUIDORES" in tabs:
                db.executemany("INSERT INTO distribuidor VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", src.execute(
                    """SELECT CodDistr, NomeDistr, Latitude, Longitude, TipoEndereco || ' ' || Endereco, NroEndereco,
                              Complemento, Bairro, Cidade, CEP, UF, Contato, Email, Telefone FROM DISTRIBUIDORES"""))
        src.close()
        print(f"{b['nome']}: {len(pmap)} produtos, {len(amap)} aplicações (emissão {um[0]})")

    db.executemany("INSERT INTO produto_aplicacao VALUES(?,?)", sorted(pa))
    db.execute("""INSERT INTO produto_linha SELECT DISTINCT pa.produto_id, a.linha_id
                  FROM produto_aplicacao pa JOIN aplicacao a ON a.id = pa.aplicacao_id""")

    # ---------- texto de busca
    db.execute("""UPDATE produto SET texto_busca = coalesce(texto_busca,'') || ' ' || upper(coalesce(descricao,'') || ' ' ||
                  coalesce(linha_cofap,'') || ' ' || coalesce(posicao,'')) || ' ' || coalesce((
                  SELECT group_concat(upper(f.nome || ' ' || r.codigo), ' ') FROM referencia_cruzada r
                  LEFT JOIN fabricante f ON f.id = r.marca_id WHERE r.produto_id = produto.id), '')""")
    db.execute("UPDATE produto SET texto_busca = remove_acento(texto_busca)")
    db.execute("UPDATE produto SET texto_busca = texto_busca || ' ' || remove_acento(marca) WHERE base <> 'cofap'")

    # ---------- regras e classificação
    regras = []     # (id, linha, tipo, descricao_rx, posicao_rx/grupo_rx, [arvore_ids])
    rid = 0
    for lid, dre, pre, dest, ob in REGRAS_COFAP:
        rid += 1
        db.execute("INSERT INTO regra_classificacao VALUES(?,?,?,?,?,?,?,?)", (rid, lid, dre, pre, " | ".join(dest), ob, "cofap", None))
        regras.append((rid, lid, "cofap", re.compile(r"^(" + dre + r")$"), re.compile(pre) if pre else None,
                       [resolver(lid, d) for d in dest]))
    for nome, lista, linhas_alvo in (("MM", RM.MM, (1, 2, 3, 4)), ("MOTO", RM.MOTO, (5,))):
        for gre, dre, dest in lista:
            for lid in linhas_alvo:
                if lid in (1, 5):
                    ids = [resolver(lid, d) for d in dest]
                    txt = dest
                else:
                    txt = [p for d in dest for p in RM.EQUIVALENTES.get(d, {}).get(lid, [])]
                    ids = [resolver(lid, p) for p in txt]
                rid += 1
                db.execute("INSERT INTO regra_classificacao VALUES(?,?,?,?,?,?,?,?)",
                           (rid, lid, dre, "", " | ".join(txt), "" if ids else "sem destino nesta linha", nome, gre))
                regras.append((rid, lid, nome, re.compile(dre) if dre else None, re.compile(gre), ids))

    lig = []
    for pid, lid in db.execute("SELECT produto_id, linha_id FROM produto_linha").fetchall():
        b, grupo, desc, pos = prod_info[pid]
        tipo = "cofap" if b["id"] in ("cofap", "pesada") else ("MOTO" if lid == 5 else "MM")
        for r_id, r_lid, r_tipo, rx1, rx2, ids in regras:
            if r_lid != lid or r_tipo != tipo:
                continue
            if tipo == "cofap":
                d, p_ = (desc or "").strip(), (pos or "").strip()
                ok = rx1.match(d) and (rx2 is None or rx2.search(p_))
            else:
                ok = rx2.search(sem_acento(grupo)) and (rx1 is None or rx1.search(sem_acento(desc)))
            if ok:
                lig += [(pid, i, r_id) for i in ids]
                break
    db.executemany("INSERT OR IGNORE INTO produto_arvore VALUES(?,?,?)", lig)

    # ---------- origem
    cof = next(um for b, um in origem if b["id"] == "cofap")
    db.executemany("INSERT INTO origem VALUES(?,?)", [
        ("fonte", "CatalogoExpresso.c01"), ("data_emissao", cof[0]), ("versao", str(cof[1])), ("versao_catalogo", str(cof[2]))] +
        [(f"base_{b['id']}", f"{b['nome']}|{um[0]}|{um[1]}") for b, um in origem] +
        [("marcas", ", ".join(r[0] for r in db.execute("SELECT DISTINCT marca FROM produto ORDER BY marca")))])
    db.commit()

    for (m,) in db.execute("SELECT DISTINCT marca FROM produto ORDER BY 1").fetchall():
        tot = db.execute("SELECT COUNT(*) FROM produto WHERE marca=?", (m,)).fetchone()[0]
        sem = db.execute("SELECT COUNT(DISTINCT id) FROM v_produto_sem_classificacao WHERE marca=?", (m,)).fetchone()[0]
        print(f"  {m}: {tot} produtos | sem classificação em alguma linha: {sem}")
    print("  aplicações por linha:", dict(db.execute("SELECT l.nome, COUNT(*) FROM aplicacao a JOIN linha l ON l.id=a.linha_id GROUP BY 1")))
    novas = Counter(como for _, como in L.saida.values())
    print("  linha das aplicações decidida por:", dict(novas))
    db.execute("VACUUM")
    db.close()
    L.gravar(CSV_LINHAS)
    with open(a.saida, "wb") as f:
        f.write(open(trabalho, "rb").read())
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Banco gravado em {a.saida}")


if __name__ == "__main__":
    main()
