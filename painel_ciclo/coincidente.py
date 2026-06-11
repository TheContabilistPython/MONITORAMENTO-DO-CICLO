# -*- coding: utf-8 -*-
"""
Monta a ESTRUTURA COINCIDENTE do painel (Tópico 1 das Orientações):
coleta as séries, calcula as três métricas, gera o sinal por indicador
e o diagnóstico agregado (cor + Ct), e grava as saídas (CSV + nota .md).
"""
import os
import datetime as dt
import pandas as pd

from . import config
from . import fontes
from . import metricas

DIR_SAIDA = os.path.join(os.path.dirname(__file__), "saidas")
os.makedirs(DIR_SAIDA, exist_ok=True)

_EMOJI = {"VERDE": "🟢", "AMARELO": "🟡", "LARANJA": "🟠",
          "VERMELHO": "🔴", "INDEFINIDO": "⚪"}
_SINAL_TXT = {1: "▲ crescendo", 0: "▬ misto", -1: "▼ caindo"}


def constroi(usar_cache=True):
    """Executa o bloco coincidente e devolve (df, diagnostico, log)."""
    catalogo = config.SERIES_COINCIDENTES
    series, log = fontes.coleta_series(catalogo, usar_cache=usar_cache)

    linhas = []
    for d in catalogo:
        s = series.get(d["chave"])
        m = (metricas.metricas_indicador(s, freq=d["freq"], tipo=d.get("tipo", "indice"))
             if s is not None else None)
        if m is None:
            linhas.append({"chave": d["chave"], "rotulo": d["rotulo"],
                           "dimensao": d["dimensao"], "freq": d["freq"],
                           "nucleo": d["nucleo"], "metricas": None,
                           "sinal": None, "composto": None})
            continue
        sinal, composto = metricas.sinal_indicador(m, inverte=d["inverte"])
        linhas.append({"chave": d["chave"], "rotulo": d["rotulo"],
                       "dimensao": d["dimensao"], "freq": d["freq"],
                       "nucleo": d["nucleo"], "metricas": m,
                       "sinal": sinal, "composto": composto})

    diag = metricas.classifica_bloco(linhas)
    df = _tabela(linhas)
    return df, diag, log, linhas, series


def _tabela(linhas):
    """DataFrame legível com as três métricas e o sinal por indicador."""
    regs = []
    for l in linhas:
        m = l["metricas"]
        regs.append({
            "indicador": l["rotulo"],
            "dimensao": l["dimensao"],
            "freq": l["freq"],
            "referencia": m["referencia"].strftime("%Y-%m") if m else "—",
            "nivel": round(m["nivel"], 3) if m else None,
            "var_mensal": round(m["var_mensal"], 2) if m else None,
            "mm3": round(m["mm3"], 3) if m else None,
            "var_mm3_vs_3m": round(m["var_mm3_3m"], 2) if m and m["var_mm3_3m"] == m["var_mm3_3m"] else None,
            "unid": m["unidade"] if m else "—",
            "nucleo": "sim" if l["nucleo"] else "—",
            "sinal": _SINAL_TXT.get(l["sinal"], "—") if l["sinal"] is not None else "sem dados",
        })
    return pd.DataFrame(regs)


_LEITURA = {
    "VERDE": "atividade coincidente em expansão disseminada — a maior parte do "
             "núcleo (produção, comércio, serviços, emprego) segue crescendo.",
    "AMARELO": "perda de ritmo na atividade coincidente, mas sem contração "
               "disseminada entre os setores do núcleo.",
    "LARANJA": "sinais de fragilidade no núcleo coincidente, com piora "
               "relevante mas ainda não generalizada nem intensa.",
    "VERMELHO": "contração ampla em formação — produção, comércio, serviços e "
                "emprego deteriorando simultaneamente.",
    "INDEFINIDO": "dados insuficientes para classificar o bloco coincidente.",
}


def _leitura(diag):
    return _LEITURA.get(diag["cor"], "—")


def grava_saidas(df, diag, log, data_ref=None):
    """Grava CSV das métricas e a nota de conjuntura (.md) do bloco coincidente."""
    data_ref = data_ref or dt.date.today().isoformat()
    csv_path = os.path.join(DIR_SAIDA, f"coincidente_{data_ref}.csv")
    md_path = os.path.join(DIR_SAIDA, f"coincidente_{data_ref}.md")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    cor = diag["cor"]
    emoji = _EMOJI.get(cor, "⚪")
    linhas_md = []
    linhas_md.append(f"# Estrutura coincidente — fechamento {data_ref}\n")
    linhas_md.append(f"## Diagnóstico do bloco: {emoji} **{cor}**  (Ct = {diag['ct']})\n")
    if diag["n_nucleo"]:
        linhas_md.append(
            f"- Indicadores de núcleo avaliados: **{diag['n_nucleo']}**  "
            f"(crescendo: {diag['n_pos']} · caindo: {diag['n_neg']})\n"
            f"- Difusão positiva: **{diag['share_pos']*100:.0f}%**  ·  "
            f"difusão negativa: **{diag['share_neg']*100:.0f}%**\n"
            f"- Intensidade média das quedas: **{diag['intensidade']:.2f}%**\n")
    linhas_md.append(f"\n> **Leitura:** {_leitura(diag)}\n")
    linhas_md.append("\n## Métricas por indicador\n")
    linhas_md.append(df.to_markdown(index=False))
    linhas_md.append(
        "\n\n_Legenda do sinal: ▲ crescendo = favorável ao ciclo · ▼ caindo = "
        "desfavorável ao ciclo · ▬ misto. Para séries invertidas (ex.: taxa de "
        "desocupação) o sinal já considera que subir é piora. `var_mensal` e "
        "`var_mm3_vs_3m` estão em % (índices), p.p. (taxas) ou nível (fluxos), "
        "conforme a coluna `unid`._\n")
    linhas_md.append("\n## Status da coleta\n")
    for k, v in log.items():
        linhas_md.append(f"- `{k}`: {v}")
    nota = "\n".join(linhas_md)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(nota)
    return csv_path, md_path, nota
