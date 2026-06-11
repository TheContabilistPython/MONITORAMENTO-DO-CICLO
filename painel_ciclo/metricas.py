# -*- coding: utf-8 -*-
"""
Métricas e regra de cor da estrutura coincidente.

Para cada indicador calcula as TRÊS métricas pedidas nas Orientações:
  1. Variação mensal dessazonalizada (M/M-1).
  2. Média móvel de três meses (MM3M) do nível.
  3. Comparação da MM3M contra os três meses imediatamente anteriores.

Depois converte o conjunto em um SINAL por indicador (+1 crescendo /
0 misto / -1 caindo) e agrega numa COR e numa pontuação Ct (0/1/2)
para o bloco coincidente do escore total.
"""
import numpy as np
import pandas as pd

DEADBAND = 0.05  # zona morta (%) para considerar "estável"


# unidade da variação conforme o tipo de série
_UNIDADE = {"indice": "%", "taxa": "p.p.", "fluxo": "nível"}


def metricas_indicador(serie, freq="M", tipo="indice"):
    """
    Calcula as três métricas para a série; devolve dict com os valores.

    O cálculo respeita o tipo da série:
      - 'indice' : variação percentual (M/M-1 e MM3M vs 3 anteriores).
      - 'taxa'   : variação em pontos percentuais (diferença).
      - 'fluxo'  : variação absoluta do nível (ex.: saldo do CAGED, que
                   pode cruzar zero e não admite variação percentual).
    """
    s = serie.dropna().sort_index()
    if len(s) < 6:
        return None

    ref = s.index[-1]
    nivel = float(s.iloc[-1])

    # Métrica 2: média móvel de três períodos (sempre sobre o nível)
    mm3 = s.rolling(3).mean()
    mm3_atual = float(mm3.iloc[-1]) if not np.isnan(mm3.iloc[-1]) else np.nan
    mm3_ant = float(mm3.iloc[-4]) if len(mm3.dropna()) >= 4 else np.nan

    if tipo == "indice":
        # Métrica 1 e 3 em variação percentual
        var1 = float(s.pct_change().iloc[-1] * 100)
        var3 = (mm3_atual / mm3_ant - 1) * 100 if mm3_ant else np.nan
    else:
        # 'taxa' e 'fluxo': diferenças absolutas (p.p. ou nível)
        var1 = float(s.iloc[-1] - s.iloc[-2])
        var3 = float(mm3_atual - mm3_ant) if not np.isnan(mm3_ant) else np.nan

    return {
        "referencia": ref,
        "nivel": nivel,
        "var_mensal": var1,        # métrica 1
        "mm3": mm3_atual,          # métrica 2 (nível)
        "var_mm3_3m": var3,        # métrica 3
        "tipo": tipo,
        "unidade": _UNIDADE.get(tipo, "%"),
        "n_obs": len(s),
    }


def sinal_indicador(m, inverte=False):
    """
    Converte as métricas em sinal direcional do ciclo:
      +1 crescendo (favorável) / 0 misto / -1 caindo (desfavorável).
    A tendência (métrica 3, MM3M) pesa mais que o último mês (métrica 1).
    'inverte' trata séries em que subir é piora (ex.: desocupação).

    Para séries de 'fluxo' (ex.: saldo do CAGED) o que importa é o NÍVEL
    da MM3M (positivo = geração líquida de postos) e sua tendência, não a
    magnitude da variação percentual.
    """
    if m is None:
        return 0, np.nan
    v1 = m["var_mensal"] if not np.isnan(m["var_mensal"]) else 0.0
    v3 = m["var_mm3_3m"] if not np.isnan(m["var_mm3_3m"]) else v1

    if m.get("tipo") == "fluxo":
        nivel_mm3 = m["mm3"]
        if inverte:
            nivel_mm3, v3 = -nivel_mm3, -v3
        # gera empregos e não está deteriorando -> positivo
        if nivel_mm3 > 0 and v3 >= 0:
            return 1, nivel_mm3
        if nivel_mm3 < 0:
            return -1, nivel_mm3
        return 0, v3

    if inverte:
        v1, v3 = -v1, -v3
    composto = 0.6 * v3 + 0.4 * v1
    if composto > DEADBAND:
        return 1, composto
    if composto < -DEADBAND:
        return -1, composto
    return 0, composto


COR_NOME = {0: "VERDE", 1: "AMARELO", 2: "LARANJA", 3: "VERMELHO"}


def classifica_bloco(linhas):
    """
    Agrega os indicadores de NÚCLEO num diagnóstico do bloco coincidente.
    Aplica a regra prática das Orientações:
      - maioria crescendo                       -> VERDE   (Ct=0)
      - perda de fôlego sem contração ampla     -> AMARELO (Ct=1)
      - prod./comércio/serviços/emprego piorando-> LARANJA/VERMELHO (Ct=2)

    'linhas' é a lista de dicts (uma por indicador) já com 'sinal',
    'composto', 'nucleo'.
    Devolve dict com cor, ct e estatísticas de difusão.
    """
    nucleo = [l for l in linhas if l["nucleo"] and l["sinal"] is not None
              and not (l["metricas"] is None)]
    n = len(nucleo)
    if n == 0:
        return {"cor": "INDEFINIDO", "ct": None, "share_pos": None,
                "share_neg": None, "n_nucleo": 0, "intensidade": None}

    n_pos = sum(1 for l in nucleo if l["sinal"] > 0)
    n_neg = sum(1 for l in nucleo if l["sinal"] < 0)
    share_pos = n_pos / n
    share_neg = n_neg / n

    quedas = [l["composto"] for l in nucleo if l["sinal"] < 0]
    intensidade = float(np.mean(quedas)) if quedas else 0.0  # média (negativa) das quedas

    if share_pos >= 0.60:
        cor, ct = "VERDE", 0
    elif share_pos >= 0.40:
        cor, ct = "AMARELO", 1
    else:
        # deterioração predominante -> distinguir laranja x vermelho pela intensidade/difusão
        if share_neg >= 0.60 and intensidade <= -0.5:
            cor, ct = "VERMELHO", 2
        else:
            cor, ct = "LARANJA", 2

    return {"cor": cor, "ct": ct, "share_pos": share_pos, "share_neg": share_neg,
            "n_nucleo": n, "n_pos": n_pos, "n_neg": n_neg, "intensidade": intensidade}
