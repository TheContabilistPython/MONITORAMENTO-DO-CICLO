# -*- coding: utf-8 -*-
"""
Monta o payload estruturado que alimenta o dashboard (Dash):
para cada indicador, as métricas, o sinal/cor e o histórico completo
(nível + média móvel de 3 períodos) para os gráficos de drill-down.
"""
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

from . import config
from . import coincidente
from . import metricas

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


def _meses_entre(referencia, hoje=None):
    """Defasagem, em meses, entre uma competência e o calendário atual."""
    hoje = hoje or dt.date.today()
    return max(0, (hoje.year - referencia.year) * 12 + hoje.month - referencia.month)


def _historico_indicador(serie, definicao, limite=36):
    """Calcula uma fotografia das métricas em cada uma das últimas competências."""
    if serie is None:
        return []
    s = serie.dropna().sort_index()
    if len(s) < 6:
        return []

    tipo = definicao.get("tipo", "indice")
    inicio = max(5, len(s) - limite)
    historico = []
    for fim in range(inicio, len(s)):
        m = metricas.metricas_indicador(
            s.iloc[:fim + 1], freq=definicao["freq"], tipo=tipo)
        if m is None:
            continue
        sinal, composto = metricas.sinal_indicador(
            m, inverte=definicao["inverte"])
        tendencia = m["var_mm3_3m"]
        if tendencia == tendencia:
            if definicao["inverte"]:
                tendencia = -tendencia
            direcao_tendencia = (1 if tendencia > metricas.DEADBAND else
                                 -1 if tendencia < -metricas.DEADBAND else 0)
        else:
            direcao_tendencia = 0
        historico.append({
            "referencia": m["referencia"].strftime("%Y-%m"),
            "nivel": round(m["nivel"], 4),
            "var_mensal": round(m["var_mensal"], 2),
            "mm3": round(m["mm3"], 4),
            "var_mm3_3m": (round(m["var_mm3_3m"], 2)
                            if m["var_mm3_3m"] == m["var_mm3_3m"] else None),
            "sinal": sinal,
            "sinal_txt": SINAL_TXT.get(sinal),
            # A interface exibe a métrica 3; esta direção mantém seta,
            # cor e valor coerentes. O panorama agregado continua usando o
            # sinal composto (métricas 1 e 3) definido em metricas.py.
            "direcao_tendencia": direcao_tendencia,
            "composto": (round(float(composto), 4)
                          if composto == composto else None),
        })
    return historico


def _panorama_mensal(indicadores, referencia_final, meses=12):
    """Série histórica da difusão usando a última leitura disponível em cada mês."""
    fim = pd.Period(referencia_final, freq="M")
    referencias = pd.period_range(end=fim, periods=meses, freq="M")
    nucleo = [i for i in indicadores if i["nucleo"] and i["freq"] == "M"]
    resultado = []

    for periodo in referencias:
        ref = str(periodo)
        linhas, competencias = [], []
        for ind in nucleo:
            disponiveis = [h for h in ind["historico"] if h["referencia"] <= ref]
            if not disponiveis:
                continue
            h = disponiveis[-1]
            competencias.append(h["referencia"])
            linhas.append({
                "nucleo": True,
                "sinal": h["sinal"],
                "composto": h["composto"],
                "metricas": h,
            })

        diag = metricas.classifica_bloco(linhas)
        estagio = ESTAGIO.get(diag["cor"], ESTAGIO["INDEFINIDO"])
        resultado.append({
            "referencia": ref,
            "cor": diag["cor"],
            "hex": estagio["hex"],
            "estagio": estagio["rotulo"],
            "share_pos": diag["share_pos"],
            "share_neg": diag["share_neg"],
            "n_pos": diag.get("n_pos", 0),
            "n_neg": diag.get("n_neg", 0),
            "n_nucleo": diag["n_nucleo"],
            "atualizados_no_mes": sum(c == ref for c in competencias),
            "competencia_min": min(competencias) if competencias else None,
            "competencia_max": max(competencias) if competencias else None,
        })
    return resultado


def montar_payload(usar_cache=True):
    """Roda o bloco coincidente e devolve um dicionário pronto para a UI."""
    _, diag, log, linhas, series = coincidente.constroi(usar_cache=usar_cache)
    fech = _fechamento_vigente()
    fontes_map = {d["chave"]: _fonte_desc(d["fonte"])
                  for d in config.SERIES_COINCIDENTES}

    catalogo_map = {d["chave"]: d for d in config.SERIES_COINCIDENTES}
    indicadores = []
    for l in linhas:
        m = l["metricas"]
        s = series.get(l["chave"])
        definicao = catalogo_map[l["chave"]]
        historico = _historico_indicador(s, definicao)
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
            "defasagem_meses": (_meses_entre(m["referencia"]) if m else None),
            "coleta_status": log.get(l["chave"], "—"),
            "origem_dado": ("cache" if log.get(l["chave"], "").startswith("CACHE")
                             else "fonte oficial"),
            "historico": historico,
            "serie": serie_payload,
        })

    # ordem das dimensões conforme aparecem no catálogo
    dimensoes = []
    for ind in indicadores:
        if ind["dimensao"] not in dimensoes:
            dimensoes.append(ind["dimensao"])

    estagio = ESTAGIO.get(diag["cor"], ESTAGIO["INDEFINIDO"])
    referencias = [i["referencia"] for i in indicadores if i["referencia"] != "—"]
    fontes_cache = [i["chave"] for i in indicadores if i["origem_dado"] == "cache"]
    # A referência do painel acompanha os dados efetivamente publicados. Isso
    # evita congelar o site quando o calendário operacional cadastrado termina.
    referencias_nucleo = [i["referencia"] for i in indicadores
                          if i["nucleo"] and i["freq"] == "M"
                          and i["referencia"] != "—"]
    referencia_panorama = (max(referencias_nucleo)
                           if referencias_nucleo else fech["referencia"])
    panorama = _panorama_mensal(indicadores, referencia_panorama)
    agora = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
    return {
        "gerado_em": agora.strftime("%d/%m/%Y %H:%M BRT"),
        "mes_corrente": agora.strftime("%Y-%m"),
        "fechamento": fech["fechamento"],
        "referencia_alvo": referencia_panorama,
        "diag": diag,
        "estagio_rotulo": estagio["rotulo"],
        "estagio_hex": estagio["hex"],
        "competencia_mais_recente": max(referencias) if referencias else None,
        "competencia_mais_antiga": min(referencias) if referencias else None,
        "fontes_cache": fontes_cache,
        "panorama_historico": panorama,
        "dimensoes": dimensoes,
        "indicadores": indicadores,
        "log": log,
    }
