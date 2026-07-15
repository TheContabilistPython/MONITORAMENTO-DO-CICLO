# -*- coding: utf-8 -*-
"""
Coletores de dados das fontes oficiais (BCB/SGS e IBGE/SIDRA).

Cada coletor devolve uma pandas.Series indexada por data (fim do mês ou
do trimestre) e ordenada cronologicamente. Resultados são gravados em
cache local (dados/) para inspeção e para não repetir downloads.
"""
import os
import time
import json
import requests
import pandas as pd

DIR_DADOS = os.path.join(os.path.dirname(__file__), "dados")
os.makedirs(DIR_DADOS, exist_ok=True)

TIMEOUT = float(os.getenv("PAINEL_HTTP_TIMEOUT", "60"))
TENTATIVAS = int(os.getenv("PAINEL_HTTP_TENTATIVAS", "3"))
_HEADERS = {"User-Agent": "PainelCicloEconomico/1.0 (monitoramento conjuntural)"}


def _get(url, tentativas=None, espera=3):
    """GET com pequena política de retry."""
    tentativas = TENTATIVAS if tentativas is None else tentativas
    ultimo_erro = None
    for i in range(tentativas):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=_HEADERS)
            if r.status_code == 200:
                return r
            ultimo_erro = f"HTTP {r.status_code}: {r.text[:160]}"
        except Exception as e:  # noqa: BLE001
            ultimo_erro = str(e)
        time.sleep(espera * (i + 1))
    raise RuntimeError(f"Falha ao acessar {url}\n  -> {ultimo_erro}")


# --------------------------------------------------------------------------
# BCB / SGS
# --------------------------------------------------------------------------
def busca_sgs(codigo, data_inicial="01/01/2015"):
    """Série temporal do Sistema Gerenciador de Séries Temporais do BCB."""
    url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
           f"?formato=json&dataInicial={data_inicial}")
    dados = _get(url).json()
    idx, val = [], []
    for reg in dados:
        idx.append(pd.to_datetime(reg["data"], format="%d/%m/%Y"))
        val.append(float(reg["valor"]))
    s = pd.Series(val, index=pd.DatetimeIndex(idx)).sort_index()
    # normaliza para fim de mês
    s.index = s.index.to_period("M").to_timestamp("M")
    return s


# --------------------------------------------------------------------------
# IBGE / SIDRA
# --------------------------------------------------------------------------
def _periodo_para_timestamp(codigo, freq):
    """Converte código SIDRA (YYYYMM mensal ou YYYYTT trimestral) em data."""
    codigo = str(codigo)
    ano = int(codigo[:4])
    p = int(codigo[4:])
    if freq == "Q":
        mes_fim = {1: 3, 2: 6, 3: 9, 4: 12}[p]
        return pd.Timestamp(ano, mes_fim, 1) + pd.offsets.MonthEnd(0)
    return pd.Timestamp(ano, p, 1) + pd.offsets.MonthEnd(0)


def busca_sidra(tabela, variavel, classif, freq="M", n_periodos=90):
    """
    Agregado do SIDRA (IBGE).
      classif: lista de tuplas (id_classificacao, id_categoria); pode ser [].
    """
    partes = [f"https://apisidra.ibge.gov.br/values/t/{tabela}",
              "n1/all", f"v/{variavel}", f"p/last%20{n_periodos}"]
    for cid, cat in classif:
        partes.append(f"c{cid}/{cat}")
    url = "/".join(partes)
    dados = _get(url).json()

    cabecalho = dados[0]
    # localiza a dimensão de período (Mês / Trimestre)
    chave_periodo = None
    for k, nome in cabecalho.items():
        if k.endswith("C") and (nome.startswith("Mês") or "Trimestre" in nome):
            chave_periodo = k
            break
    if chave_periodo is None:
        chave_periodo = "D3C"  # padrão observado nas tabelas usadas

    idx, val = [], []
    for reg in dados[1:]:
        bruto = reg.get("V")
        if bruto in (None, "-", "...", "..", "X", ""):
            continue
        try:
            valor = float(str(bruto).replace(",", "."))
        except ValueError:
            continue
        idx.append(_periodo_para_timestamp(reg[chave_periodo], freq))
        val.append(valor)
    if not idx:
        raise RuntimeError(f"SIDRA tabela {tabela} v{variavel} retornou vazio: {url}")
    return pd.Series(val, index=pd.DatetimeIndex(idx)).sort_index()


# --------------------------------------------------------------------------
# Orquestração: baixa todas as séries de um catálogo
# --------------------------------------------------------------------------
def coleta_series(catalogo, usar_cache=True):
    """
    Recebe a lista de definições (config.SERIES_COINCIDENTES) e devolve:
      series : dict chave -> pandas.Series
      log    : dict chave -> mensagem de status
    Séries 'derivado' são resolvidas no fim, a partir das já coletadas.
    """
    series, log = {}, {}
    pendentes_derivados = []

    for d in catalogo:
        chave, fonte = d["chave"], d["fonte"]
        cache = os.path.join(DIR_DADOS, f"{chave}.csv")
        if fonte["tipo"] == "derivado":
            pendentes_derivados.append(d)
            continue
        try:
            if fonte["tipo"] == "sgs":
                s = busca_sgs(fonte["codigo"])
            elif fonte["tipo"] == "sidra":
                s = busca_sidra(fonte["tabela"], fonte["variavel"],
                                fonte.get("classif", []), freq=d["freq"])
            else:
                raise ValueError(f"tipo de fonte desconhecido: {fonte['tipo']}")
            s.name = chave
            s.to_csv(cache, header=["valor"])
            series[chave] = s
            log[chave] = f"OK  ({len(s)} obs, ult. {s.index[-1].date()})"
        except Exception as e:  # noqa: BLE001
            if usar_cache and os.path.exists(cache):
                s = pd.read_csv(cache, index_col=0, parse_dates=True)["valor"]
                s.name = chave
                series[chave] = s
                log[chave] = f"CACHE usado (fonte falhou: {str(e)[:70]})"
            else:
                log[chave] = f"FALHOU: {str(e)[:120]}"

    # resolve derivados
    for d in pendentes_derivados:
        chave, fonte = d["chave"], d["fonte"]
        base = series.get(fonte["base"])
        if base is None:
            log[chave] = f"FALHOU: série base '{fonte['base']}' indisponível"
            continue
        if fonte["op"] == "diff":
            s = base.diff().dropna()
        else:
            raise ValueError(f"operação derivada desconhecida: {fonte['op']}")
        s.name = chave
        s.to_csv(os.path.join(DIR_DADOS, f"{chave}.csv"), header=["valor"])
        series[chave] = s
        log[chave] = f"OK derivado de {fonte['base']} ({len(s)} obs)"

    return series, log
