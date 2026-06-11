# -*- coding: utf-8 -*-
"""
Textos explicativos por indicador para a página de detalhe do dashboard:
"O que é?", "Por que é importante?" e "Como interpretar?".
Escritos para um leitor leigo, em 2–3 frases cada.
"""

TEXTOS = {
    "ibcbr": {
        "o_que": "Índice de Atividade Econômica do Banco Central (IBC-Br). É uma "
                 "espécie de 'prévia mensal do PIB': agrega indústria, comércio, "
                 "serviços e agropecuária em um único índice, já dessazonalizado.",
        "por_que": "É a leitura mais rápida e abrangente de como a economia está "
                   "agora. Costuma antecipar a direção do PIB trimestral e é "
                   "acompanhado de perto pelo Banco Central nas decisões de juros.",
        "como": "Alta na média móvel de 3 meses indica expansão corrente; quedas "
                "por três meses ou mais sugerem perda de fôlego da economia.",
    },
    "pib_total": {
        "o_que": "Produto Interno Bruto: a soma de tudo o que o país produz em bens "
                 "e serviços. Série trimestral de volume, dessazonalizada (IBGE).",
        "por_que": "É a medida oficial e mais completa da atividade econômica — a "
                   "régua usada para dizer se a economia cresceu ou encolheu.",
        "como": "Crescimento positivo trimestre contra trimestre indica expansão. "
                "Dois trimestres seguidos de queda caracterizam a chamada "
                "'recessão técnica'.",
    },
    "pib_industria": {
        "o_que": "Parcela do PIB gerada pela indústria (extrativa, transformação, "
                 "construção e utilidades), pela ótica da oferta.",
        "por_que": "A indústria é o setor mais sensível ao ciclo: tende a cair "
                   "primeiro e mais forte nas desacelerações.",
        "como": "Compare a direção da indústria com o PIB total: se a indústria "
                "cai enquanto o resto cresce, o ciclo pode estar virando.",
    },
    "pib_servicos": {
        "o_que": "Parcela do PIB gerada pelos serviços, pela ótica da oferta — "
                 "cerca de 70% da economia brasileira.",
        "por_que": "Por seu tamanho, é o setor que define a tendência de fundo do "
                   "PIB; é mais estável que a indústria, mas quando cai indica "
                   "fraqueza disseminada.",
        "como": "Queda persistente em serviços é sinal forte de desaceleração, "
                "pois o setor costuma resistir mais às viradas de ciclo.",
    },
    "pib_fbcf": {
        "o_que": "Formação Bruta de Capital Fixo: o investimento em máquinas, "
                 "equipamentos e construção, pela ótica da demanda.",
        "por_que": "É o componente mais cíclico da demanda: empresários só investem "
                   "quando confiam no futuro. Também antecipa a capacidade de "
                   "crescimento da economia.",
        "como": "Quedas fortes e seguidas na FBCF costumam anteceder recessões; "
                "recuperação do investimento sinaliza retomada sustentada.",
    },
    "pim_geral": {
        "o_que": "Produção física da indústria geral (PIM-PF/IBGE), índice "
                 "dessazonalizado com base 2022=100.",
        "por_que": "Mede o pulso fabril do país em tempo quase real. A indústria "
                   "reage rápido a juros, crédito e demanda — é termômetro "
                   "antecipado do ciclo.",
        "como": "Acompanhe a média móvel de 3 meses: acima do período anterior, "
                "indústria em expansão; abaixo, contração.",
    },
    "pim_transf": {
        "o_que": "Produção física da indústria de transformação — fábricas que "
                 "transformam insumos em produtos (alimentos, veículos, químicos…).",
        "por_que": "É o miolo da indústria e o elo mais ligado ao emprego "
                   "industrial e às cadeias produtivas domésticas.",
        "como": "Se a transformação cai enquanto a extrativa sobe, a fraqueza é "
                "doméstica (demanda interna), não de commodities.",
    },
    "pim_extrativa": {
        "o_que": "Produção física da indústria extrativa: petróleo, gás e minérios.",
        "por_que": "Pesa nas exportações e na renda nacional, mas segue lógica "
                   "própria (projetos de longo prazo, preços internacionais).",
        "como": "Movimentos da extrativa podem mascarar o ciclo doméstico — por "
                "isso compare sempre com a indústria de transformação.",
    },
    "pim_bk": {
        "o_que": "Produção de bens de capital: máquinas e equipamentos usados para "
                 "produzir outros bens.",
        "por_que": "É proxy direta do investimento. Empresas só encomendam máquinas "
                   "quando esperam demanda futura — antecipa o ciclo.",
        "como": "Alta sustentada sugere ciclo de investimento em curso; queda "
                "forte antecipa desaceleração da atividade à frente.",
    },
    "pim_bi": {
        "o_que": "Produção de bens intermediários: insumos industriais (aço, "
                 "químicos, embalagens) consumidos pelas cadeias produtivas.",
        "por_que": "Reflete a demanda 'de dentro' da indústria: se as fábricas "
                   "compram menos insumo, a produção futura tende a cair.",
        "como": "Funciona como sinal antecedente curto da própria indústria — "
                "vira antes da produção final.",
    },
    "pmc_restrito": {
        "o_que": "Volume de vendas do varejo restrito (PMC/IBGE): supermercados, "
                 "vestuário, móveis, farmácias etc., dessazonalizado.",
        "por_que": "Retrata o consumo corrente das famílias, motor de ~60% do PIB "
                   "pela demanda.",
        "como": "Queda persistente no varejo indica famílias sob aperto (renda, "
                "juros, inadimplência) e desaceleração do consumo.",
    },
    "pmc_ampliado": {
        "o_que": "Varejo ampliado: inclui também veículos, peças e material de "
                 "construção — itens caros e sensíveis a crédito.",
        "por_que": "Por depender de financiamento, é mais cíclico que o varejo "
                   "restrito: reage rápido a juros e confiança.",
        "como": "Se o ampliado cai mais que o restrito, o aperto de crédito está "
                "pesando; é alerta de desaceleração à frente.",
    },
    "pms_total": {
        "o_que": "Volume de serviços (PMS/IBGE): transporte, serviços às famílias, "
                 "informação, profissionais e administrativos, dessazonalizado.",
        "por_que": "Serviços são o maior empregador do país; sua trajetória define "
                   "se a desaceleração está disseminada ou restrita à indústria.",
        "como": "Serviços costumam ser resilientes: quando entram em queda "
                "persistente, o ciclo provavelmente já virou.",
    },
    "pnad_ocupada": {
        "o_que": "Número de pessoas ocupadas (PNAD Contínua/IBGE), em milhares, no "
                 "trimestre móvel.",
        "por_que": "Emprego é a ponte entre atividade e renda das famílias: define "
                   "consumo, inadimplência e bem-estar.",
        "como": "Ocupação reage com algum atraso ao ciclo. Queda da ocupação "
                "confirma desaceleração; alta sustenta o consumo.",
    },
    "pnad_desocup": {
        "o_que": "Taxa de desocupação (PNAD Contínua): % da força de trabalho que "
                 "procura emprego e não encontra. Trimestre móvel.",
        "por_que": "É o indicador social mais visível do ciclo — e um dos últimos "
                   "a piorar nas recessões e a melhorar nas retomadas.",
        "como": "Atenção: aqui, SUBIR é piora. No cartão, a cor já considera isso "
                "(vermelho = desemprego subindo).",
    },
    "pnad_massa": {
        "o_que": "Massa real de rendimentos: total de salários da economia "
                 "(ocupados × rendimento médio), descontada a inflação.",
        "por_que": "É o combustível do consumo das famílias: quando a massa cresce, "
                   "o varejo e os serviços tendem a crescer junto.",
        "como": "Massa caindo em termos reais = menos dinheiro circulando = "
                "pressão baixista sobre consumo nos meses seguintes.",
    },
    "pnad_rend": {
        "o_que": "Rendimento médio real do trabalho (PNAD Contínua), descontada a "
                 "inflação.",
        "por_que": "Separa o efeito 'mais gente trabalhando' do efeito 'salários "
                   "maiores' dentro da massa de rendimentos.",
        "como": "Rendimento caindo com ocupação alta sugere vagas de pior "
                "qualidade; ambos caindo é sinal claro de ciclo fraco.",
    },
    "caged_estoque": {
        "o_que": "Estoque total de empregos formais (carteira assinada) apurado "
                 "pelo Novo CAGED.",
        "por_que": "O emprego formal é o de maior renda e estabilidade; seu estoque "
                   "mostra a tendência de fundo do mercado de trabalho.",
        "como": "Crescimento contínuo do estoque = mercado formal saudável; "
                "estagnação ou queda confirma deterioração do ciclo.",
    },
    "caged_saldo": {
        "o_que": "Saldo mensal do emprego formal: admissões menos desligamentos "
                 "(Novo CAGED). Aqui derivado da variação do estoque.",
        "por_que": "É o fluxo do mercado de trabalho — mostra na margem se as "
                   "empresas estão contratando ou demitindo.",
        "como": "Saldo positivo = geração líquida de vagas. Atenção à forte "
                "sazonalidade: compare a média móvel de 3 meses, não um mês isolado.",
    },
}
