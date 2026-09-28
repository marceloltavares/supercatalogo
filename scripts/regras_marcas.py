"""
Regras de classificação das bases novas (Magneti Marelli e Motocicletas) nas árvores.

Cada regra: (grupo do catálogo (regex), descrição do produto (regex ou ""), destinos)
  - destinos = lista de "Grupo > Subgrupo" da árvore Passeio (base MM) ou Moto (base Moto).
  - Para Caminhão, Ônibus e Trator o gerar_banco.py procura o subgrupo equivalente
    pelo nome (ver EQUIVALENTES abaixo para forçar um destino).
  - A primeira regra que casar vale. Lista vazia = fica em "Sem classificação".
Regex sem acento e em maiúsculas (o texto é comparado sem acentos).
"""

# ------------------------------------------------------------------ Magneti Marelli -> Passeio
MM = [
    # Motor - alimentação
    (r"BOMBA ELETRICA DE COMBUSTIVEL|BOMBAS MECANICAS DE COMBUSTIVEL|BOMBAS DE ALTA PRESSAO|BOMBAS ELETRICAS DA PARTIDA|MODULOS DE COMBUSTIVEIS|VALVULAS REGULADORA DA BOMBA|REGULADORES DE PRESSAO",
     "", ["Sistema de Alimentação (Combustível) > Bomba de Combustível (Elétrica, Mecânica)"]),
    (r"PRE FILTRO|GUARNICAO DA FLANGE", "", ["Sistema de Alimentação (Combustível) > Bomba de Combustível (Elétrica, Mecânica)"]),
    (r"FILTROS DE COMBUSTIVEIS|FILTROS DE OLEO COMBUSTIVEL", "", ["Sistema de Alimentação (Combustível) > Filtro de Combustível"]),
    (r"INJETORES DE COMBUSTIVEL|INJETORES DIESEL|COMPONENTES DE CARBURADORES|SOLENOIDES DE PARTIDA A FRIO|KIT MANUTENCAO",
     "", ["Sistema de Alimentação (Combustível) > Bicos Injetores/Carburador"]),
    (r"CORPO DE BORBOLETA|SENSORES DE POSICAO DE BORBOLETA|MOTORES DE PASSO|SOLENOIDES DE MARCHA LENTA|PEDAIS DE ACELERACAO|SENSORES DE POSICAO DO PEDAL",
     "", ["Sistema de Alimentação (Combustível) > Corpo de Borboleta (TBI)"]),
    (r"SENSORES DE MASSA DE AR|SENSORES DE PRESSAO ABSOLUTA|FILTROS DO SENSOR DE PRESSAO|SENSORES DE TEMPERATURA DO AR",
     "", ["Sistema de Alimentação (Combustível) > Sensores (Boia, Fluxo de Ar - MAF)"]),
    (r"SENSORES DE NIVEL", "", ["Painel de Instrumentos e Sensores > Boia de Combustível"]),
    # Motor - ignição
    (r"VELAS DE IGNICAO|VELAS AQUECEDORAS", "", ["Sistema de Ignição > Velas de Ignição"]),
    (r"CABOS DE VELA", "", ["Sistema de Ignição > Cabos de Vela"]),
    (r"BOBINAS DE IGNICAO", "", ["Sistema de Ignição > Bobinas de Ignição"]),
    (r"MODULOS DE IGNICAO|ROTORES DO DISTRIBUIDOR|TAMPAS DO DISTRIBUIDOR", "", ["Sistema de Ignição > Módulo de Ignição/Distribuidor"]),
    # Motor - interno, lubrificação, correias, turbo
    (r"VALVULAS DE MOTOR", "", ["Cabeçote e Componentes > Válvulas (Admissão, Escape)"]),
    (r"JOGOS DE ANEIS", "", ["Bloco do Motor e Componentes Internos > Anéis de Segmento"]),
    (r"BOMBAS DE OLEO", "", ["Sistema de Lubrificação > Bomba de Óleo"]),
    (r"FILTROS DE OLEO$", "", ["Sistema de Lubrificação > Filtro de Óleo"]),
    (r"REFRIGERADORES DE OLEO", "", ["Sistema de Lubrificação > Cárter"]),
    (r"KIT DISTRIBUICAO", "", ["Correias e Polias > Correia Dentada/Comando"]),
    (r"TENSORES DA CORREIA|REFIL DOS TENSORES|GUIAS DA CORREIA|POLIAS|DAMPERS DA CORREIA|ENGRENAGENS DE APOIO DA CORREIA",
     "", ["Correias e Polias > Polias e Tensionadores"]),
    (r"INTERCOOLERS|BLOCOS PARA INTERCOOLER", "", ["Superalimentação (Turbo/Compressor) > Intercooler"]),
    (r"MANGUEIRAS", r"INTERCOOLER|TURBINA|COLETOR DE ADMISSAO", ["Superalimentação (Turbo/Compressor) > Intercooler"]),
    (r"MANGUEIRAS", "", ["Circulação de Água > Mangueiras do Radiador e Arrefecimento"]),
    (r"FILTROS DE AR", "", ["Manutenção Geral > Filtro de Ar do Motor"]),
    # Arrefecimento
    (r"^RADIADORES$|BLOCOS PARA RADIADORES", "", ["Radiador e Componentes > Radiador de Água"]),
    (r"ELETROVENTILADORES|EMBREAGENS VISCOSAS|VISCO-FANS|HELICES|RESISTENCIAS DE VENTOINHAS", "", ["Radiador e Componentes > Ventoinha do Radiador (Eletroventilador)"]),
    (r"DEFLETORES", "", ["Radiador e Componentes > Defletor da Ventoinha"]),
    (r"BOMBAS D. AGUA", "", ["Circulação de Água > Bomba D'água"]),
    (r"VALVULAS TERMOSTATICAS", "", ["Circulação de Água > Válvula Termostática"]),
    (r"TANQUES DE COMPENSACAO|TAMPAS PLASTICAS", "", ["Circulação de Água > Reservatório de Expansão"]),
    (r"FLUIDOS PARA RADIADORES|FILTROS DE REFRIGERACAO", "", ["Circulação de Água > Aditivo/Fluido de Arrefecimento"]),
    (r"SENSORES DE TEMPERATURA DE AGUA", "", ["Sensores e Interruptores > Sensor de Temperatura da Água"]),
    # Interruptores (pela descrição)
    (r"INTERRUPTORES", r"PRESSAO DE OLEO", ["Sistema de Lubrificação > Sensores de Óleo (Nível, Pressão)"]),
    (r"INTERRUPTORES", r"TERMICO", ["Sensores e Interruptores > Interruptor Térmico da Ventoinha (Cebolão)"]),
    (r"INTERRUPTORES", r"LUZ DE RE|LUZ DO FREIO", ["Iluminação > Relés e Módulos de Iluminação"]),
    (r"INTERRUPTORES", r"DIRECAO HIDRAULICA", ["Sistema de Direção > Bomba de Direção Hidráulica"]),
    (r"INTERRUPTORES", r"EMBREAGEM", ["Embreagem > Cabos e Garfos"]),
    (r"INTERRUPTORES", r"TRANSFERENCIA", ["Diferencial > Carcaça e Juntas"]),
    (r"INTERRUPTORES", r"PNEUMATICO", ["Sistema Hidráulico de Freio > Servo Freio (Hidrovácuo)"]),
    (r"INTERRUPTORES", "", []),
    # Elétrico
    (r"BATERIAS", "", ["Geração e Armazenamento de Energia > Bateria"]),
    (r"RETIFICADORES", "", ["Geração e Armazenamento de Energia > Alternador"]),
    (r"REGULADORES DE VOLTAGEM", "", ["Geração e Armazenamento de Energia > Regulador de Voltagem"]),
    (r"RELES", "", ["Componentes Elétricos Diversos > Relés e Fusíveis"]),
    (r"FAROIS", "", ["Iluminação > Faróis (Bloco Óptico)"]),
    (r"LANTERNAS", "", ["Iluminação > Lanternas Traseiras"]),
    (r"LAMPADAS", "", ["Iluminação > Lâmpadas Diversas"]),
    (r"PAINEIS DE COMANDO", "", ["Painel de Instrumentos e Sensores > Painel de Instrumentos Completo"]),
    (r"SENSORES DE (DETONACAO|FASE|ROTACAO|VELOCIDADE|PRESSAO DO RAIL)|SENSORES DE TEMPERATURA (DO PAINEL|DA PARTIDA|DOS GASES)",
     "", ["Painel de Instrumentos e Sensores > Sensores Diversos (Temperatura, Velocidade, Rotação, etc.)"]),
    (r"ELETROBOMBAS", "", ["Componentes Elétricos Diversos > Limpador de Para-brisa (Motor, Braços, Palhetas)"]),
    (r"PALHETAS", "", ["Manutenção Geral > Palhetas do Limpador"]),
    # Freios, direção, transmissão
    (r"SENSORES ABS", "", ["Sistema ABS/Controle de Estabilidade > Sensores de Roda (ABS)"]),
    (r"SENSORES DE DESGATE", "", ["Freio a Disco > Pastilhas de Freio"]),
    (r"ATUADORES HIDRAULICOS", "", ["Embreagem > Cilindro Mestre e Auxiliar"]),
    (r"COMPONENTES DE CAMBIO AUTOMATIZADO", "", ["Caixa de Câmbio (Automática / Automatizada) > Módulos Eletrônicos"]),
    # Climatização
    (r"COMPRESSORES", "", ["Ar Condicionado > Compressor do Ar Condicionado"]),
    (r"CONDENSADORES", "", ["Ar Condicionado > Condensador"]),
    (r"FILTROS DE CABINE", "", ["Ar Condicionado > Filtro de Cabine/Anti-pólen"]),
    (r"FILTROS SECADORES", "", ["Ar Condicionado > Mangueiras e Tubulações"]),
    (r"SENSORES DE TEMPERATURA AMBIENTE", "", ["Ar Condicionado > Pressostatos e Sensores"]),
    (r"RADIADORES DO AR QUENTE", "", ["Aquecimento / Ventilação > Radiador de Ar Quente"]),
    (r"MOTORES DOS VENTILADORES INTERNOS", "", ["Aquecimento / Ventilação > Motor do Ventilador Interno (Ventoinha)"]),
    (r"RESISTENCIAS DE CAIXAS EVAPORADORAS", "", ["Aquecimento / Ventilação > Resistência da Ventilação"]),
    # Emissões
    (r"SENSORES DE OXIGENIO|SONDAS LAMBDAS|SENSORES NOX", "", ["Controle de Emissões > Sonda Lambda (Sensor de Oxigênio)"]),
    (r"INJETORES ARLA32", "", ["Controle de Emissões > Válvula EGR"]),
]

# ------------------------------------------------------------------ Motocicletas -> Moto
MOTO = [
    (r"AMORTECEDORES", "", ["Suspensão Traseira > Amortecedor Convencional (Duplo-choque)"]),
    (r"TUBOS INTERNOS", "", ["Suspensão Dianteira > Tubo Interno (Bengala)"]),
    (r"CAIXAS DE DIRECAO", "", ["Mesa de Direção > Caixa de Direção (Rolamentos cônicos/esferas)"]),
    (r"PASTILHAS PARA FREIO", "", ["Freio Dianteiro > Pastilha de Freio (Orgânica/Metálica/Sinterizada)", "Freio Traseiro > Pastilhas de Freio"]),
    (r"PATINS DE FREIO", "", ["Freio Traseiro > Sapatas/Lonas de Freio"]),
    (r"CABOS DE FREIOS", "", ["Freio Traseiro > Haste/Varão de Acionamento"]),
    (r"CABOS DE EMBREAGEM", "", ["Embreagem (Multidisco em banho de óleo / Seca) > Cabo de Embreagem"]),
    (r"CABOS DE ACELERADOR|CABOS DO AFOGADOR", "", ["Sistema de Alimentação (Combustível) > Afogador (Mecanismo)"]),
    (r"CABOS DE (VELOCIMETROS|CONTAGIROS)", "", ["Instrumentação e Controles > Painel de Instrumentos (Velocímetro, Conta-giros, Hodômetro, Marcador Comb., Luzes Espia)"]),
    (r"KITS TRANSMISSAO", "", ["Transmissão Final > Corrente de Transmissão"]),
    (r"KITS MOTOR|PISTAO E ANEIS", "", ["Bloco do Motor e Componentes Internos > Pistões"]),
    (r"BIELAS", "", ["Bloco do Motor e Componentes Internos > Bielas"]),
    (r"VALVULAS DE MOTOR", "", ["Cabeçote e Comando de Válvulas > Válvulas de Admissão e Escape"]),
    (r"FILTROS DE AR", "", ["Sistema de Admissão de Ar > Elemento do Filtro de Ar (Papel, Espuma, Lavável)"]),
    (r"FILTROS DE OLEO", "", ["Sistema de Lubrificação > Filtro de Óleo (Elemento/Cartucho)"]),
    (r"FILTROS DE COMBUSTIVEIS", "", ["Sistema de Alimentação (Combustível) > Filtro de Combustível"]),
    (r"BOMBA ELETRICA DE COMBUSTIVEL", "", ["Sistema de Alimentação (Combustível) > Bomba de Combustível (Externa/Interna ao tanque - Injeção)"]),
    (r"BATERIAS", "", ["Geração e Armazenamento > Bateria (Chumbo-ácido/Gel/Lítio)"]),
    (r"REGULADORES DE VOLTAGEM", "", ["Geração e Armazenamento > Retificador/Regulador de Voltagem"]),
    (r"SUPORTES E ESCOVAS", "", ["Sistema de Partida > Motor de Partida"]),
    (r"RELES", "", ["Iluminação e Sinalização > Relé dos Piscas"]),
    (r"LAMPADAS", "", ["Iluminação e Sinalização > Farol Dianteiro (Lâmpada Halógena/LED/Xenon)"]),
    (r"VELAS DE IGNICAO", "", ["Sistema de Ignição > Vela de Ignição"]),
    (r"BOBINAS DE IGNICAO", "", ["Sistema de Ignição > Bobina de Ignição"]),
    (r"SENSORES DE TEMPERATURA", "", ["Sensores e Atuadores Diversos (Injeção/Eletrônica) > Sensor de Temperatura do Motor/Água (ECT)"]),
    (r"INTERRUPTORES", "", ["Instrumentação e Controles > Comandos de Punho (Luzes, Pisca, Buzina, Partida, Corta-corrente)"]),
]

# ------------------------------------------------------------------ Equivalências nas outras árvores
# Destino da árvore Passeio ("Grupo > Subgrupo") -> caminho completo nas árvores
# 2 = Caminhão, 3 = Ônibus, 4 = Trator. Lista vazia ou ausente = "Sem classificação" naquela linha.
C, O, T = 2, 3, 4
EQUIVALENTES = {
    "Aquecimento / Ventilação > Motor do Ventilador Interno (Ventoinha)": {
        C: ["Climatização > Ventilação e Aquecimento (Ar Quente) > Ventilador/Blower da Cabine"],
        O: ["Climatização > Calefação/Aquecimento > Ventilador/Blower da Calefação"],
        T: ["Climatização (Cabine Fechada) > Ventilação e Aquecimento > Ventilador/Blower da Cabine"]},
    "Aquecimento / Ventilação > Radiador de Ar Quente": {
        C: ["Climatização > Ventilação e Aquecimento (Ar Quente) > Radiador de Ar Quente"],
        O: ["Climatização > Calefação/Aquecimento > Radiador de Ar Quente (Utiliza água do motor)"],
        T: ["Climatização (Cabine Fechada) > Ventilação e Aquecimento > Radiador de Ar Quente"]},
    "Aquecimento / Ventilação > Resistência da Ventilação": {
        C: ["Climatização > Ventilação e Aquecimento (Ar Quente) > Ventilador/Blower da Cabine"],
        O: ["Climatização > Calefação/Aquecimento > Ventilador/Blower da Calefação"],
        T: ["Climatização (Cabine Fechada) > Ventilação e Aquecimento > Ventilador/Blower da Cabine"]},
    "Ar Condicionado > Compressor do Ar Condicionado": {
        C: ["Climatização > Ar Condicionado > Compressor"],
        O: ["Climatização > Ar Condicionado > Compressor (Acoplado ao motor/Semi-hermético elétrico)"],
        T: ["Climatização (Cabine Fechada) > Ar Condicionado > Compressor e Embreagem Magnética"]},
    "Ar Condicionado > Condensador": {
        C: ["Climatização > Ar Condicionado > Condensador e Eletroventilador"],
        O: ["Climatização > Ar Condicionado > Condensador (Com Eletroventiladores)"],
        T: ["Climatização (Cabine Fechada) > Ar Condicionado > Condensador e Eletroventilador"]},
    "Ar Condicionado > Filtro de Cabine/Anti-pólen": {
        C: ["Climatização > Ventilação e Aquecimento (Ar Quente) > Filtro de Cabine (Anti-pólen)"],
        O: ["Climatização > Ventilação e Exaustão > Filtros de Ar da Cabine/Salão (Anti-pólen)"],
        T: ["Climatização (Cabine Fechada) > Filtragem de Ar da Cabine > Filtro de Ar Interno/Recirculação (Anti-pólen/Carvão Ativado)"]},
    "Ar Condicionado > Mangueiras e Tubulações": {
        C: ["Climatização > Ar Condicionado > Filtro Secador/Acumulador"],
        O: ["Climatização > Ar Condicionado > Filtro Secador/Acumulador"],
        T: ["Climatização (Cabine Fechada) > Ar Condicionado > Filtro Secador/Acumulador"]},
    "Ar Condicionado > Pressostatos e Sensores": {
        C: ["Climatização > Ar Condicionado > Pressostatos e Sensores"],
        O: ["Climatização > Ar Condicionado > Sensores de Temperatura (Interna, Externa, Evaporador)"],
        T: ["Climatização (Cabine Fechada) > Ar Condicionado > Pressostatos e Sensores de Temperatura"]},
    "Bloco do Motor e Componentes Internos > Anéis de Segmento": {
        C: ["Motor > Bloco do Motor e Componentes Internos > Anéis de Segmento"],
        O: ["Motor > Bloco do Motor e Componentes Internos > Anéis de Segmento (Compressão, Raspador)"],
        T: ["Motor (Diesel Agrícola) > Bloco do Motor e Componentes Internos > Anéis de Segmento"]},
    "Cabeçote e Componentes > Válvulas (Admissão, Escape)": {
        C: ["Motor > Cabeçote e Comando de Válvulas > Válvulas de Admissão e Escape"],
        O: ["Motor > Cabeçote e Comando de Válvulas > Válvulas de Admissão", "Motor > Cabeçote e Comando de Válvulas > Válvulas de Escape"],
        T: ["Motor (Diesel Agrícola) > Cabeçote e Comando de Válvulas > Válvulas de Admissão e Escape"]},
    "Caixa de Câmbio (Automática / Automatizada) > Módulos Eletrônicos": {
        C: ["Transmissão > Caixa de Câmbio (Manual/Automatizada) > Módulo Eletrônico (TCU - Automatizada)"],
        O: ["Transmissão > Caixa de Câmbio > Módulo Eletrônico da Transmissão (TCU - Automatizada/Automática)"],
        T: ["Transmissão > Caixa de Câmbio > Módulo Eletrônico (Powershift/CVT)"]},
    "Circulação de Água > Aditivo/Fluido de Arrefecimento": {
        C: ["Arrefecimento do Motor > Líquido de Arrefecimento / Aditivo"],
        T: ["Arrefecimento do Motor > Sensores e Fluidos > Líquido de Arrefecimento / Aditivo"]},
    "Circulação de Água > Bomba D'água": {
        C: ["Arrefecimento do Motor > Bomba Dágua"],
        T: ["Arrefecimento do Motor > Componentes Principais > Bomba Dágua"]},
    "Circulação de Água > Mangueiras do Radiador e Arrefecimento": {
        C: ["Arrefecimento do Motor > Mangueiras e Tubulações"],
        T: ["Arrefecimento do Motor > Mangueiras e Tubulações > Mangueira Superior do Radiador",
            "Arrefecimento do Motor > Mangueiras e Tubulações > Mangueira Inferior do Radiador"]},
    "Circulação de Água > Reservatório de Expansão": {
        C: ["Arrefecimento do Motor > Reservatório de Expansão e Tampa"],
        T: ["Arrefecimento do Motor > Componentes Principais > Reservatório de Expansão e Tampa"]},
    "Circulação de Água > Válvula Termostática": {
        C: ["Arrefecimento do Motor > Válvula Termostática e Carcaça"],
        T: ["Arrefecimento do Motor > Componentes Principais > Válvula Termostática e Carcaça"]},
    "Componentes Elétricos Diversos > Limpador de Para-brisa (Motor, Braços, Palhetas)": {
        C: ["Elétrico > Componentes Elétricos Diversos > Bomba do Lavador"],
        O: ["Elétrico > Componentes Elétricos Diversos > Bomba do Lavador de Para-brisa"],
        T: ["Cabine/Plataforma do Operador > Vidros e Espelhos > Lavador de Para-brisa (Bomba, Reservatório, Esguichos)"]},
    "Componentes Elétricos Diversos > Relés e Fusíveis": {
        C: ["Elétrico > Chicotes Elétricos > Caixa de Fusíveis e Relés"],
        O: ["Elétrico > Chicotes Elétricos > Caixa de Fusíveis e Relés (Central Elétrica)"],
        T: ["Elétrico > Chicotes Elétricos e Conectores > Caixa de Fusíveis e Relés"]},
    "Controle de Emissões > Sonda Lambda (Sensor de Oxigênio)": {
        C: ["Motor > Sistema SCR > Sensores de NOx (Entrada/Saída)"],
        O: ["Motor > Sistema SCR > Sensores de NOx (Entrada/Saída)"],
        T: ["Motor (Diesel Agrícola) > Sistema de Pós-Tratamento (Emissões) > Sensores (NOx, Temperatura, Nível Arla)"]},
    "Controle de Emissões > Válvula EGR": {
        C: ["Motor > Sistema SCR > Unidade Dosadora/Injetor de Arla 32"],
        O: ["Motor > Sistema SCR > Unidade Dosadora/Injetor de Arla 32"],
        T: ["Motor (Diesel Agrícola) > Sistema de Pós-Tratamento (Emissões) > Injetor de Arla 32"]},
    "Correias e Polias > Correia Dentada/Comando": {
        C: ["Motor > Correias e Polias > Correia Poly-V/Correias em V"],
        O: ["Motor > Correias e Polias > Correia Poly-V/Correias em V"],
        T: ["Motor (Diesel Agrícola) > Correias e Polias > Correia Poly-V/Correias em V"]},
    "Correias e Polias > Polias e Tensionadores": {
        C: ["Motor > Correias e Polias > Tensionadores Automáticos/Manuais"],
        O: ["Motor > Correias e Polias > Tensionadores Automáticos / Manuais"],
        T: ["Motor (Diesel Agrícola) > Correias e Polias > Tensionadores Automáticos/Manuais"]},
    "Diferencial > Carcaça e Juntas": {
        C: ["Transmissão > Diferencial > Bloqueio do Diferencial (Mecanismo Pneumático/Elétrico)"],
        O: ["Transmissão > Diferencial > Bloqueio do Diferencial"],
        T: ["Transmissão > Eixo Dianteiro Motriz (Tração Dianteira Auxiliar - TDA/4x4) > Caixa de Transferência/Acoplamento TDA (Embreagem/Engrenagem)"]},
    "Embreagem > Cabos e Garfos": {
        C: ["Transmissão > Embreagem > Garfo e Pivô"],
        O: ["Transmissão > Embreagem > Garfo e Pivô de Acionamento"],
        T: ["Transmissão > Embreagem Principal > Garfo e Pivô"]},
    "Embreagem > Cilindro Mestre e Auxiliar": {
        C: ["Transmissão > Embreagem > Cilindro Mestre e Auxiliar"],
        O: ["Transmissão > Embreagem > Cilindro Mestre de Embreagem", "Transmissão > Embreagem > Atuador Hidráulico (Servo Embreagem)/Cilindro Auxiliar"],
        T: ["Transmissão > Embreagem Principal > Cilindro Mestre e Auxiliar (Hidráulico)"]},
    "Freio a Disco > Pastilhas de Freio": {
        C: ["Freios > Freio de Roda (Tambor/Disco) > Pastilhas de Freio"],
        O: ["Freios > Freio de Roda (Tambor/Disco) > Pastilhas de Freio"],
        T: ["Freios > Freio de Serviço (Eixo Traseiro) > Pastilhas / Placas de Fricção"]},
    "Geração e Armazenamento de Energia > Alternador": {
        C: ["Elétrico > Geração e Armazenamento > Alternador (24V)"],
        O: ["Elétrico > Geração e Armazenamento de Energia > Alternador (24V, alta amperagem)"],
        T: ["Elétrico > Geração e Armazenamento > Alternador"]},
    "Geração e Armazenamento de Energia > Bateria": {
        C: ["Elétrico > Geração e Armazenamento > Baterias"],
        O: ["Elétrico > Geração e Armazenamento de Energia > Baterias (Ligadas em série)"],
        T: ["Elétrico > Geração e Armazenamento > Bateria"]},
    "Geração e Armazenamento de Energia > Regulador de Voltagem": {
        C: ["Elétrico > Geração e Armazenamento > Regulador de Voltagem"],
        O: ["Elétrico > Geração e Armazenamento de Energia > Regulador de Voltagem (Interno/Externo)"],
        T: ["Elétrico > Geração e Armazenamento > Regulador de Voltagem"]},
    "Iluminação > Faróis (Bloco Óptico)": {
        C: ["Elétrico > Iluminação Externa > Faróis Principais (Bloco Óptico, Lâmpadas)"],
        O: ["Elétrico > Iluminação Externa > Faróis Principais (Bloco Óptico)"],
        T: ["Elétrico > Iluminação > Faróis Dianteiros (Transporte/Trabalho)"]},
    "Iluminação > Lanternas Traseiras": {
        C: ["Elétrico > Iluminação Externa > Lanternas Traseiras (Conjunto, Lâmpadas/LEDs)"],
        O: ["Elétrico > Iluminação Externa > Lanternas Traseiras (Posição, Freio, Ré, Pisca)"],
        T: ["Elétrico > Iluminação > Lanternas Traseiras (Posição, Freio, Pisca)"]},
    "Iluminação > Lâmpadas Diversas": {
        C: ["Elétrico > Iluminação Externa > Faróis Principais (Bloco Óptico, Lâmpadas)"],
        O: ["Elétrico > Iluminação Externa > Lâmpadas dos Faróis (Halógena, LED)"],
        T: ["Elétrico > Iluminação > Faróis Dianteiros (Transporte/Trabalho)"]},
    "Iluminação > Relés e Módulos de Iluminação": {
        C: ["Elétrico > Painel de Instrumentos e Controles > Interruptores (Alavanca de Seta/Farol, Botões)"],
        O: ["Elétrico > Painel de Instrumentos e Controles > Interruptores e Comandos (Setas, Farol, Limpador, etc)"],
        T: ["Elétrico > Painel de Instrumentos e Controles > Interruptores (Luzes, Pisca, TDP, Tração, Bloqueio)"]},
    "Manutenção Geral > Filtro de Ar do Motor": {
        C: ["Motor > Sistema de Admissão de Ar > Filtro de Ar Primário e Secundário"],
        O: ["Motor > Sistema de Admissão de Ar > Filtro de Ar Primário"],
        T: ["Motor (Diesel Agrícola) > Sistema de Admissão de Ar > Filtro de Ar Primário (Elemento principal)"]},
    "Manutenção Geral > Palhetas do Limpador": {
        C: ["Elétrico > Componentes Elétricos Diversos > Palhetas do Limpador"],
        O: ["Elétrico > Componentes Elétricos Diversos > Braços e Palhetas do Limpador"],
        T: ["Cabine/Plataforma do Operador > Vidros e Espelhos > Limpador de Para-brisa (Motor, Braço, Palheta)"]},
    "Painel de Instrumentos e Sensores > Boia de Combustível": {
        C: ["Motor > Sistema de Alimentação Diesel > Unidade de Sucção/Boia"],
        O: ["Motor > Sistema de Alimentação Diesel > Unidade de Sucção/Boia de Nível"],
        T: ["Motor (Diesel Agrícola) > Sistema de Alimentação Diesel > Boia de Nível/Sensor"]},
    "Painel de Instrumentos e Sensores > Painel de Instrumentos Completo": {
        C: ["Elétrico > Painel de Instrumentos e Controles > Conjunto do Painel (Velocímetro, Conta-giros, Indicadores)"],
        O: ["Elétrico > Painel de Instrumentos e Controles > Conjunto do Painel (Velocímetro, Conta-giros, Indicadores)"],
        T: ["Elétrico > Painel de Instrumentos e Controles > Conjunto de Instrumentos (Velocímetro/Tacômetro, Horímetro, Nível Comb., Temp.)"]},
    "Painel de Instrumentos e Sensores > Sensores Diversos (Temperatura, Velocidade, Rotação, etc.)": {
        C: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível)"],
        O: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível, etc.)"],
        T: ["Elétrico > Sensores Diversos > Sensor de Rotação (Motor, TDP, Roda)"]},
    "Radiador e Componentes > Defletor da Ventoinha": {
        C: ["Arrefecimento do Motor > Defletor/Carenagem da Ventoinha"],
        T: ["Arrefecimento do Motor > Componentes Principais > Defletor/Carenagem da Ventoinha"]},
    "Radiador e Componentes > Radiador de Água": {
        C: ["Arrefecimento do Motor > Radiador de Água"],
        T: ["Arrefecimento do Motor > Componentes Principais > Radiador de Água (Com tela de proteção contra detritos)"]},
    "Radiador e Componentes > Ventoinha do Radiador (Eletroventilador)": {
        C: ["Arrefecimento do Motor > Ventoinha/Hélice"],
        T: ["Arrefecimento do Motor > Componentes Principais > Ventoinha/Hélice (Fixa/Viscosa/Elétrica)"]},
    "Sensores e Interruptores > Interruptor Térmico da Ventoinha (Cebolão)": {
        C: ["Arrefecimento do Motor > Sensor de Temperatura / Nível"],
        O: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível, etc.)"],
        T: ["Arrefecimento do Motor > Sensores e Fluidos > Sensor de Temperatura da Água"]},
    "Sensores e Interruptores > Sensor de Temperatura da Água": {
        C: ["Arrefecimento do Motor > Sensor de Temperatura / Nível"],
        O: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível, etc.)"],
        T: ["Arrefecimento do Motor > Sensores e Fluidos > Sensor de Temperatura da Água"]},
    "Sistema ABS/Controle de Estabilidade > Sensores de Roda (ABS)": {
        C: ["Freios > Sistema ABS/EBS > Sensores de Roda"],
        O: ["Freios > Sistema ABS/EBS > Sensores de Roda (Velocidade)"]},
    "Sistema Hidráulico de Freio > Servo Freio (Hidrovácuo)": {
        C: ["Freios > Produção e Armazenamento de Ar > Regulador de Pressão (Governador)"],
        O: ["Freios > Produção e Armazenamento de Ar > Regulador de Pressão (Governador)"],
        T: ["Freios > Freio de Reboque (Opcional) > Sistema Pneumático de Freio para Reboque (Se equipado)"]},
    "Sistema de Alimentação (Combustível) > Bicos Injetores/Carburador": {
        C: ["Motor > Sistema de Alimentação Diesel > Bicos Injetores Eletrônicos"],
        O: ["Motor > Sistema de Alimentação Diesel > Bicos Injetores (Mecânicos, Eletrônicos - Common Rail)"],
        T: ["Motor (Diesel Agrícola) > Sistema de Alimentação Diesel > Bicos Injetores (Mecânicos/Eletrônicos)"]},
    "Sistema de Alimentação (Combustível) > Bomba de Combustível (Elétrica, Mecânica)": {
        C: ["Motor > Sistema de Alimentação Diesel > Bomba Alimentadora (Baixa Pressão)"],
        O: ["Motor > Sistema de Alimentação Diesel > Bomba Alimentadora de Combustível (Baixa Pressão)"],
        T: ["Motor (Diesel Agrícola) > Sistema de Alimentação Diesel > Bomba Alimentadora (Baixa Pressão - Mecânica/Elétrica)"]},
    "Sistema de Alimentação (Combustível) > Corpo de Borboleta (TBI)": {
        C: ["Motor > Sistema de Alimentação Diesel > Sensor do Pedal do Acelerador"],
        O: ["Motor > Sistema de Alimentação Diesel > Sensor de Posição do Acelerador"],
        T: ["Motor (Diesel Agrícola) > Sistema de Alimentação Diesel > Sensor do Pedal do Acelerador (Eletrônico)"]},
    "Sistema de Alimentação (Combustível) > Filtro de Combustível": {
        C: ["Motor > Sistema de Alimentação Diesel > Filtro Secundário de Combustível"],
        O: ["Motor > Sistema de Alimentação Diesel > Filtro Secundário de Combustível"],
        T: ["Motor (Diesel Agrícola) > Sistema de Alimentação Diesel > Filtro Principal de Combustível"]},
    "Sistema de Alimentação (Combustível) > Sensores (Boia, Fluxo de Ar - MAF)": {
        C: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível)"],
        O: ["Elétrico > Componentes Elétricos Diversos > Sensores Diversos (Temperatura, Pressão, Nível, etc.)"],
        T: ["Elétrico > Sensores Diversos > Sensor de Pressão (Óleo, Combustível, Hidráulico)"]},
    "Sistema de Direção > Bomba de Direção Hidráulica": {
        C: ["Direção > Caixa de Direção Hidráulica > Carcaça e Componentes Internos"],
        O: ["Direção > Caixa de Direção Hidráulica > Válvulas Internas"],
        T: ["Direção (Hidrostática/Hidráulica) > Sistema Hidrostático > Bomba Hidráulica (Pode ser a principal do trator)"]},
    "Sistema de Lubrificação > Bomba de Óleo": {
        C: ["Motor > Sistema de Lubrificação > Bomba de Óleo"],
        O: ["Motor > Sistema de Lubrificação > Bomba de Óleo"],
        T: ["Motor (Diesel Agrícola) > Sistema de Lubrificação > Bomba de Óleo"]},
    "Sistema de Lubrificação > Cárter": {
        C: ["Motor > Sistema de Lubrificação > Trocador de Calor do Óleo"],
        O: ["Motor > Sistema de Lubrificação > Trocador de Calor do Óleo (Radiador de Óleo)"],
        T: ["Motor (Diesel Agrícola) > Sistema de Lubrificação > Trocador de Calor do Óleo"]},
    "Sistema de Lubrificação > Filtro de Óleo": {
        C: ["Motor > Sistema de Lubrificação > Filtro de Óleo Lubrificante (Principal, By-pass/Centrífugo)"],
        O: ["Motor > Sistema de Lubrificação > Filtro de Óleo (Elemento, Blindado)"],
        T: ["Motor (Diesel Agrícola) > Sistema de Lubrificação > Filtro de Óleo Lubrificante"]},
    "Sistema de Lubrificação > Sensores de Óleo (Nível, Pressão)": {
        C: ["Motor > Sistema de Lubrificação > Sensor de Nível/Pressão/Temperatura do Óleo"],
        O: ["Motor > Sistema de Lubrificação > Sensor de Pressão de Óleo"],
        T: ["Motor (Diesel Agrícola) > Sistema de Lubrificação > Sensor de Nível/Pressão do Óleo"]},
    "Superalimentação (Turbo/Compressor) > Intercooler": {
        C: ["Motor > Superalimentação (Turbo) > Intercooler (Ar-Ar)"],
        O: ["Motor > Superalimentação (Turbo/Compressor) > Intercooler (Resfriador Ar-Ar)"],
        T: ["Motor (Diesel Agrícola) > Superalimentação (Turbo) > Intercooler (Ar-Ar)"]},
    # Ignição (velas, cabos, bobinas, distribuidor): linha diesel não tem nó próprio -> sem classificação
}

# ------------------------------------------------------------------ Linha por montadora (bases novas)
# Montadoras que não existem na base Cofap: define a linha das aplicações (1 Passeio, 2 Caminhão,
# 3 Ônibus, 4 Trator/Máquinas, 5 Moto). As demais seguem a regra geral do gerar_banco.py.
LINHA_MONTADORA = {
    4: ["CATERPILLAR", "MASSEY FERGUSON", "NEW HOLLAND", "VALMET", "CASE", "JI.CASE", "CLARK", "FIAT ALLIS",
        "MULLER", "TEMA TERRA", "KOMATSU", "AGCO", "CBT", "HYSTER", "VALTRA", "TEREX", "DYNAPAC", "SANTA MATILDE",
        "MALVES", "POCLAIN", "VERMEER TRENCHER", "TOYAMA", "BOBCAT", "CNH", "ZECTOR", "MARCOPLAN", "IDEAL",
        "YANMAR", "YALE", "JCB", "LINK-BELT", "DRESSER", "KUBOTA", "SANTAL", "DEGONG", "CHAMPION GRADER",
        "CAMECO", "DOOSAN", "KOBELCO", "LIEBHERR", "ATLAS COPCO", "PERKINS", "MAXION", "KHD"],
    2: ["MWM", "CUMMINS", "EATON", "ZF", "WABCO", "SINOTRUCK", "THERMOKING", "EL-DETALLE", "DAIMIER", "LINHA PESADA"],
    3: ["VOLARE", "BUSSCAR", "INDUSCAR", "MASCARELLO", "CAIO", "MARCOPOLO", "COMIL", "NEOBUS", "IRIZAR"],
    5: ["HARLEY DAVIDSON", "KTM", "CAN-AM"],
}

# Base Motocicletas: marca pelo código do produto (códigos com "MM" são Magneti Marelli)
def marca_moto(codigo, grupo):
    import re
    if "MM" in (codigo or "").upper() or re.search(r"BATERIA|BOBINA|RELE|REGULADOR|SENSOR|VELA|LAMPADA|INTERRUPTOR|SUPORTES E ESCOVAS|BOMBA ELETRICA|FILTRO", grupo or ""):
        return "Magneti Marelli"
    return "Cofap"
