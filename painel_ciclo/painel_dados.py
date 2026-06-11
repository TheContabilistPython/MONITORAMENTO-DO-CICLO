# -*- coding: utf-8 -*-
"""
Monta o payload estruturado que alimenta o dashboard (Dash):
para cada indicador, as métricas, o sinal/cor e o histórico completo
(nível + média móvel de 3 períodos) para os gráficos de drill-down.
"""
import datetime as dt
import numpy as np

from . import config
from . import coincidente

# cor da "luz" de cada instrumento a partir do sinal direcional do ciclo
COR_SINAL = {1: "verde", 0: "amarelo", -1: "vermelho", None: "cinza"}
SINAL_TXT = {1: "crescendo", 0: "misto", -1: "caindo", None: "sem dados"}

# bloco -> estágio do ciclo (palavra para o leigo) + hex da cor
ESTAGIO = {
    "VERDE":      {"rotulo": "EXPANSÃO",            "hex": "#2e9e4f"},
    "AMARELO":    {"rotulo": "DESACELERAÇÃO",       "hex": "#e8c12a"},
    "LARANJA":    {"rotulo": "ALERTA RECESSIVO",    "hex": "#e8821a"},
    "VERMELHO":   {"rotulo": "RECESSÃO PROVÁVEL",   "hex": "#d8362a"},
    "ROXO":       {"rotulo": "CONTRAÇÃO AMPLA",     "hex": "#7a3ea8"},
    "INDEFINIDO": {"rotulo": "SEM DADOS",           "hex": "#888888"},
}
COR_HEX = {"verde": "#2e9e4f", "amarelo": "#e8c12a",
           "vermelho": "#d8362a", "cinza": "#888888"}


def _fechamento_vigente(hoje=None):
    hoje = hoje or dt.date.today()
    futuros = [c for c in config.CALENDARIO_2026
               if dt.date.fromisoformat(c["fechamento"]) >= hoje]
    return (futuros[0] if futuros else config.CALENDARIO_2026[-1])


def _fonte_desc(fonte):
    if fonte["tipo"] == "sgs":
        return f"Banco Central do Brasil — SGS, série {fonte['codigo']}"
    if fonte["tipo"] == "sidra":
        return f"IBGE — SIDRA, tabela {fonte['tabela']}"
    return "Derivado: 1ª diferença do estoque de vínculos (BCB/SGS 28763)"


def montar_payload(usar_cache=True):
    """Roda o bloco coincidente e devolve um dicionário pronto para a UI."""
    _, diag, log, linhas, series = coincidente.constroi(usar_cache=usar_cache)
    fech = _fechamento_vigente()
    fontes_map = {d["chave"]: _fonte_desc(d["fonte"])
                  for d in config.SERIES_COINCIDENTES}

    indicadores = []
    for l in linhas:
        m = l["metricas"]
        s = series.get(l["chave"])
        serie_payload = {"datas": [], "valores": [], "mm3": []}
        if s is not None and len(s):
            s = s.dropna().sort_index()
            mm3 = s.rolling(3).mean()
            serie_payload = {
                "datas": [d.strftime("%Y-%m") for d in s.index],
                "valores": [round(float(v), 4) for v in s.values],
                "mm3": [None if np.isnan(x) else round(float(x), 4) for x in mm3.values],
            }
        cor = COR_SINAL.get(l["sinal"])
        indicadores.append({
            "chave": l["chave"],
            "rotulo": l["rotulo"],
            "fonte_desc": fontes_map.get(l["chave"], "—"),
            "dimensao": l["dimensao"],
            "freq": l["freq"],
            "nucleo": l["nucleo"],
            "tipo": (m["tipo"] if m else "indice"),
            "unidade": (m["unidade"] if m else "%"),
            "cor": cor,
            "cor_hex": COR_HEX.get(cor, "#888888"),
            "sinal_txt": SINAL_TXT.get(l["sinal"]),
            "referencia": (m["referencia"].strftime("%Y-%m") if m else "—"),
            "nivel": (round(m["nivel"], 3) if m else None),
            "var_mensal": (round(m["var_mensal"], 2) if m else None),
            "mm3": (round(m["mm3"], 3) if m else None),
            "var_mm3_3m": (round(m["var_mm3_3m"], 2)
                           if m and m["var_mm3_3m"] == m["var_mm3_3m"] else None),
            "serie": serie_payload,
        })

    # ordem das dimensões conforme aparecem no catálogo
    dimensoes = []
    for ind in indicadores:
        if ind["dimensao"] not in dimensoes:
            dimensoes.append(ind["dimensao"])

    estagio = ESTAGIO.get(diag["cor"], ESTAGIO["INDEFINIDO"])
    return {
        "gerado_em": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "fechamento": fech["fechamento"],
        "referencia_alvo": fech["referencia"],
        "diag": diag,
        "estagio_rotulo": estagio["rotulo"],
        "estagio_hex": estagio["hex"],
        "dimensoes": dimensoes,
        "indicadores": indicadores,
        "log": log,
    }
