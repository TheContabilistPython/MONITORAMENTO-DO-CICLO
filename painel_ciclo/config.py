# -*- coding: utf-8 -*-
"""
Configuração do Painel de Monitoramento do Ciclo Econômico.

Define o calendário operacional de 2026 e o catálogo de séries da
ESTRUTURA COINCIDENTE (Tópico 1 das Orientações).

Cada série aponta para sua fonte oficial:
  - 'sgs'      -> API do Banco Central (séries temporais SGS)
  - 'sidra'    -> API do IBGE (agregados SIDRA)
  - 'derivado' -> calculada a partir de outra série já baixada
"""

# --------------------------------------------------------------------------
# Setores exibidos na home do painel (dashboard e site estático).
# 'slug' (ASCII, sem acentos) é usado nos ids de navegação: ids com acento
# quebram o casamento clientside dos callbacks do Dash.
# --------------------------------------------------------------------------
SETORES = [
    {"nome": "Atividade Agregada", "slug": "atividade", "icone": "📈",
     "dims": ["Atividade agregada mensal", "Atividade agregada trimestral"]},
    {"nome": "Indústria", "slug": "industria", "icone": "🏭", "dims": ["Indústria"]},
    {"nome": "Comércio", "slug": "comercio", "icone": "🛒", "dims": ["Comércio"]},
    {"nome": "Serviços", "slug": "servicos", "icone": "🧳", "dims": ["Serviços"]},
    {"nome": "Trabalho e Renda", "slug": "trabalho", "icone": "👥",
     "dims": ["Mercado de trabalho"]},
    {"nome": "Emprego Formal", "slug": "emprego", "icone": "📋",
     "dims": ["Emprego formal"]},
]

# --------------------------------------------------------------------------
# Calendário operacional 2026 (Tabela 5 das Orientações)
# Fechamento sempre no dia 20, ou próximo dia útil.
# --------------------------------------------------------------------------
CALENDARIO_2026 = [
    {"fechamento": "2026-06-22", "referencia": "2026-04", "mm3": ["2026-02", "2026-03", "2026-04"],
     "comp_3m": ["2025-11", "2025-12", "2026-01"], "comp_6m": "2025-10", "pib_tri": None},
    {"fechamento": "2026-07-20", "referencia": "2026-05", "mm3": ["2026-03", "2026-04", "2026-05"],
     "comp_3m": ["2025-12", "2026-01", "2026-02"], "comp_6m": "2025-11", "pib_tri": None},
    {"fechamento": "2026-08-20", "referencia": "2026-06", "mm3": ["2026-04", "2026-05", "2026-06"],
     "comp_3m": ["2026-01", "2026-02", "2026-03"], "comp_6m": "2025-12", "pib_tri": None},
    {"fechamento": "2026-09-21", "referencia": "2026-07", "mm3": ["2026-05", "2026-06", "2026-07"],
     "comp_3m": ["2026-02", "2026-03", "2026-04"], "comp_6m": "2026-01", "pib_tri": "2026-Q2"},
    {"fechamento": "2026-10-20", "referencia": "2026-08", "mm3": ["2026-06", "2026-07", "2026-08"],
     "comp_3m": ["2026-03", "2026-04", "2026-05"], "comp_6m": "2026-02", "pib_tri": None},
    {"fechamento": "2026-11-23", "referencia": "2026-09", "mm3": ["2026-07", "2026-08", "2026-09"],
     "comp_3m": ["2026-04", "2026-05", "2026-06"], "comp_6m": "2026-03", "pib_tri": None},
    {"fechamento": "2026-12-21", "referencia": "2026-10", "mm3": ["2026-08", "2026-09", "2026-10"],
     "comp_3m": ["2026-05", "2026-06", "2026-07"], "comp_6m": "2026-04", "pib_tri": "2026-Q3"},
]

# --------------------------------------------------------------------------
# Catálogo de séries da estrutura COINCIDENTE
#
# campos:
#   chave    : identificador interno
#   rotulo   : nome legível
#   dimensao : agrupamento (Tabela 1 das Orientações)
#   freq     : 'M' mensal | 'Q' trimestral
#   inverte  : True quando "subir" é PIORA (ex.: taxa de desocupação)
#   nucleo   : True se entra na contagem de difusão do bloco coincidente Ct
#   fonte    : especificação da origem dos dados
# --------------------------------------------------------------------------
SERIES_COINCIDENTES = [
    # --- Atividade agregada mensal -----------------------------------------
    {"chave": "ibcbr", "rotulo": "IBC-Br (dessaz.)", "dimensao": "Atividade agregada mensal",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sgs", "codigo": 24364}},

    # --- Atividade agregada trimestral (PIB - contexto) --------------------
    {"chave": "pib_total", "rotulo": "PIB total (dessaz.)", "dimensao": "Atividade agregada trimestral",
     "freq": "Q", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 1621, "variavel": 584, "classif": [("11255", "90707")]}},
    {"chave": "pib_industria", "rotulo": "PIB indústria (oferta)", "dimensao": "Atividade agregada trimestral",
     "freq": "Q", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 1621, "variavel": 584, "classif": [("11255", "90691")]}},
    {"chave": "pib_servicos", "rotulo": "PIB serviços (oferta)", "dimensao": "Atividade agregada trimestral",
     "freq": "Q", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 1621, "variavel": 584, "classif": [("11255", "90696")]}},
    {"chave": "pib_fbcf", "rotulo": "PIB FBCF (demanda/investimento)", "dimensao": "Atividade agregada trimestral",
     "freq": "Q", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 1621, "variavel": 584, "classif": [("11255", "93406")]}},

    # --- Indústria (PIM-PF, dessaz.) ---------------------------------------
    {"chave": "pim_geral", "rotulo": "PIM indústria geral", "dimensao": "Indústria",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sidra", "tabela": 8888, "variavel": 12607, "classif": [("544", "129314")]}},
    {"chave": "pim_transf", "rotulo": "PIM transformação", "dimensao": "Indústria",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 8888, "variavel": 12607, "classif": [("544", "129316")]}},
    {"chave": "pim_extrativa", "rotulo": "PIM extrativa", "dimensao": "Indústria",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 8888, "variavel": 12607, "classif": [("544", "129315")]}},
    {"chave": "pim_bk", "rotulo": "PIM bens de capital", "dimensao": "Indústria",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 8887, "variavel": 12607, "classif": [("543", "129278")]}},
    {"chave": "pim_bi", "rotulo": "PIM bens intermediários", "dimensao": "Indústria",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 8887, "variavel": 12607, "classif": [("543", "129283")]}},

    # --- Comércio (PMC volume, dessaz.) ------------------------------------
    {"chave": "pmc_restrito", "rotulo": "PMC varejo restrito", "dimensao": "Comércio",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sidra", "tabela": 8880, "variavel": 7170, "classif": [("11046", "56734")]}},
    {"chave": "pmc_ampliado", "rotulo": "PMC varejo ampliado", "dimensao": "Comércio",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 8881, "variavel": 7170, "classif": [("11046", "56736")]}},

    # --- Serviços (PMS volume, dessaz.) ------------------------------------
    {"chave": "pms_total", "rotulo": "PMS volume de serviços", "dimensao": "Serviços",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sidra", "tabela": 5906, "variavel": 7168, "classif": [("11046", "56726")]}},

    # --- Mercado de trabalho (PNAD Contínua mensal, trimestre móvel) -------
    {"chave": "pnad_ocupada", "rotulo": "População ocupada (PNAD)", "dimensao": "Mercado de trabalho",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sidra", "tabela": 6318, "variavel": 1641, "classif": [("629", "32387")]}},
    {"chave": "pnad_desocup", "rotulo": "Taxa de desocupação (PNAD)", "dimensao": "Mercado de trabalho",
     "freq": "M", "inverte": True, "nucleo": False, "tipo": "taxa",
     "fonte": {"tipo": "sidra", "tabela": 6381, "variavel": 4099, "classif": []}},
    {"chave": "pnad_massa", "rotulo": "Massa real de rendimentos (PNAD)", "dimensao": "Mercado de trabalho",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sidra", "tabela": 6392, "variavel": 6293, "classif": []}},
    {"chave": "pnad_rend", "rotulo": "Rendimento real médio (PNAD)", "dimensao": "Mercado de trabalho",
     "freq": "M", "inverte": False, "nucleo": False,
     "fonte": {"tipo": "sidra", "tabela": 6390, "variavel": 5933, "classif": []}},

    # --- Emprego formal (Novo CAGED via estoque SGS 28763) -----------------
    {"chave": "caged_estoque", "rotulo": "Estoque de vínculos formais (CAGED)", "dimensao": "Emprego formal",
     "freq": "M", "inverte": False, "nucleo": True,
     "fonte": {"tipo": "sgs", "codigo": 28763}},
    {"chave": "caged_saldo", "rotulo": "Saldo de emprego formal (CAGED)", "dimensao": "Emprego formal",
     "freq": "M", "inverte": False, "nucleo": False, "tipo": "fluxo",
     "fonte": {"tipo": "derivado", "base": "caged_estoque", "op": "diff"}},
]
