# -*- coding: utf-8 -*-
"""
Painel do Ciclo Econômico — visual "Indicadores / Panorama Macroeconômico".

Navegação em três níveis (conforme esboços em `novo visual/`):
  1. HOME ........ cartões coloridos por SETOR + Termômetro do Ciclo à direita.
  2. SETOR ....... cartões coloridos dos INDICADORES daquele setor.
  3. DETALHE ..... página do indicador: série completa com intervalo típico,
                   últimos 12 meses e fichas "O que é / Por que importa /
                   Como interpretar" (como em `industria.png`).

A cor do cartão e a seta dizem tudo para o leigo:
  verde ↑/↗ melhorando · amarelo → estável · laranja ↘ piorando ·
  vermelho ↓ piorando forte. Para séries invertidas (desocupação), a cor
  já considera que subir é piora.

Rodar:
    python -m painel_ciclo.dashboard
    # abra http://127.0.0.1:8050 no navegador
"""
import math
from urllib.parse import quote

import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

from . import config
from . import painel_dados
from .textos import TEXTOS

# ---------------------------------------------------------------- paleta clara
BG = "#eef0f5"
CARTAO_BRANCO = "#ffffff"
NAVY = "#1c2e6b"          # títulos e ponteiro do termômetro
TXT_CINZA = "#6b7280"

VERDE = "#179a55"
AMARELO = "#f2b600"
LARANJA = "#f08c00"
VERMELHO = "#e23a2e"
ROXO = "#6a3fa0"

CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"
FONTES_CSS = ["https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700"
              "&family=Inter:wght@400;500;600;700&display=swap"]
F_TITULO = "'Playfair Display', Georgia, serif"
F_CORPO = "'Inter', 'Segoe UI', Arial, sans-serif"

SOMBRA = "0 4px 14px rgba(28,46,107,0.10)"

# ---------------------------------------------------------------- setores
# definidos em config.SETORES (compartilhados com o exportador estático)
SETORES = config.SETORES


def _setor_por_slug(slug):
    return next((s for s in SETORES if s["slug"] == slug), None)


# ---------------------------------------------------------------- formatação
def _fmt_num(v, dec=1):
    if v is None:
        return "—"
    return f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _fmt_var(v, unidade="%"):
    if v is None:
        return "—"
    sinal = "+" if v >= 0 else "−"
    a = abs(v)
    if unidade == "%":
        return f"{sinal}{a:.1f}".replace(".", ",") + "%"
    if unidade == "p.p.":
        return f"{sinal}{a:.1f}".replace(".", ",") + " p.p."
    return f"{sinal}{a:,.0f}".replace(",", ".")


def _mes_pt(ref):
    """'2026-04' -> 'abr. 2026'"""
    try:
        ano, mes = ref.split("-")
        nomes = ["jan", "fev", "mar", "abr", "mai", "jun",
                 "jul", "ago", "set", "out", "nov", "dez"]
        return f"{nomes[int(mes) - 1]}. {ano}"
    except Exception:
        return ref or "—"


# ---------------------------------------------------------------- status/seta
def _momentum(ind):
    """Momentum da série (MM3M vs 3M anteriores) normalizado pela volatilidade."""
    var = ind.get("var_mm3_3m")
    if var is None:
        return 0.0
    mm3 = [v for v in (ind.get("serie", {}).get("mm3") or []) if v is not None]
    difs = [b - a for a, b in zip(mm3[-25:-1], mm3[-24:])]
    if len(difs) >= 6:
        media = sum(difs) / len(difs)
        dp = math.sqrt(sum((d - media) ** 2 for d in difs) / len(difs))
        if dp > 1e-12:
            return max(-2.0, min(2.0, var / (3 * dp)))
    return 1.0 if var > 0 else (-1.0 if var < 0 else 0.0)


def _status_de(cor, z):
    """(cor do payload, momentum) -> dict cor_hex / ângulo da seta / rótulo."""
    if cor == "verde":
        if z >= 0.9:
            return {"hex": VERDE, "ang": -90, "rotulo": "melhora forte"}
        return {"hex": VERDE, "ang": -45, "rotulo": "melhorando"}
    if cor == "vermelho":
        if z <= -0.9:
            return {"hex": VERMELHO, "ang": 90, "rotulo": "piora forte"}
        return {"hex": LARANJA, "ang": 45, "rotulo": "piorando"}
    return {"hex": AMARELO, "ang": 0, "rotulo": "estável"}


DEADBAND = 0.05  # zona morta para considerar a tendência "estável"


def _status_ind(ind):
    """
    Cor/seta do cartão do INDICADOR.

    Para séries de índice, segue a TENDÊNCIA exibida no cartão (MM3M vs 3
    meses anteriores): tendência negativa nunca aparece verde, mesmo que o
    setor esteja bem — as cores acompanham a escala da Tabela 4.
    Para taxas (desocupação) e fluxos (saldo CAGED) usa o sinal do payload,
    que já trata a inversão (subir = piora).
    """
    z = _momentum(ind)
    if ind.get("tipo", "indice") == "indice":
        v3 = ind.get("var_mm3_3m")
        if v3 is None:
            cor = "amarelo"
        elif v3 > DEADBAND:
            cor = "verde"
        elif v3 < -DEADBAND:
            cor = "vermelho"
        else:
            cor = "amarelo"
        return _status_de(cor, z)
    return _status_de(ind.get("cor"), z)


def _status_setor(grupo):
    """Agrega os indicadores de um setor em um status único."""
    com_sinal = [i for i in grupo if i.get("sinal_txt") != "sem dados"]
    if not com_sinal:
        return _status_de("amarelo", 0.0)
    stats = [_status_ind(i) for i in com_sinal]
    pos = sum(1 for s in stats if s["hex"] == VERDE)
    neg = sum(1 for s in stats if s["hex"] in (LARANJA, VERMELHO))
    share = pos / len(stats)
    z_med = sum(_momentum(i) for i in com_sinal) / len(com_sinal)
    if share >= 0.6:
        return _status_de("verde", z_med)
    if share >= 0.4 and neg < len(stats) / 2:
        return _status_de("amarelo", z_med)
    return _status_de("vermelho", z_med)


def _conta_altas(grupo):
    """Quantos indicadores do grupo estão com tendência de alta (verde)."""
    return sum(1 for i in grupo if _status_ind(i)["hex"] == VERDE)


# ---------------------------------------------------------------- SVG helpers
def _svg_uri(corpo, w, h):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}">{corpo}</svg>')
    return "data:image/svg+xml;utf8," + quote(svg)


def _seta_icone(ang, tam=64):
    """Círculo branco vazado com seta rotacionada (como nos esboços)."""
    corpo = (
        f'<circle cx="32" cy="32" r="27" stroke="white" stroke-width="2.6" fill="none"/>'
        f'<g transform="rotate({ang} 32 32)">'
        f'<path d="M21 32 H42 M34 23 L43 32 L34 41" stroke="white" stroke-width="4" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    return html.Img(src=_svg_uri(corpo, 64, 64),
                    style={"width": f"{tam}px", "height": f"{tam}px", "flexShrink": "0"})


def _spark_branca(serie, w=250, h=30):
    vals = [v for v in (serie.get("valores") or []) if v is not None][-36:]
    if len(vals) < 2:
        return html.Div(style={"height": f"{h}px"})
    vmin, vmax = min(vals), max(vals)
    amp = (vmax - vmin) or 1.0
    pad = 2
    pts = []
    for i, v in enumerate(vals):
        x = pad + i * (w - 2 * pad) / (len(vals) - 1)
        y = h - pad - (v - vmin) / amp * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    corpo = (f'<polyline points="{" ".join(pts)}" fill="none" stroke="white" '
             f'stroke-width="1.6" opacity="0.9" stroke-linejoin="round"/>')
    return html.Img(src=_svg_uri(corpo, w, h),
                    style={"width": "100%", "height": f"{h}px",
                           "marginTop": "auto", "paddingTop": "10px"})


def _termometro(p):
    """Medidor semicircular 0–100 da difusão positiva do núcleo (estilo esboço)."""
    diag = p["diag"]
    val = (diag.get("share_pos") or 0) * 100
    cx, cy, R = 130, 132, 96
    # segmentos proporcionais à Tabela 4 (escore 0–8 invertido p/ 0–100):
    # roxo 7–8, vermelho 5–6, laranja 3–4, amarelo 2, verde 0–1
    segs = [(0, 22, ROXO), (22, 44, VERMELHO), (44, 67, LARANJA),
            (67, 78, AMARELO), (78, 100, VERDE)]

    def ponto(v, raio):
        th = math.radians(180 - v * 1.8)
        return cx + raio * math.cos(th), cy - raio * math.sin(th)

    arcos = []
    for a, b, cor in segs:
        x0, y0 = ponto(a + 1.0, R)
        x1, y1 = ponto(b - 1.0, R)
        arcos.append(f'<path d="M {x0:.1f} {y0:.1f} A {R} {R} 0 0 1 {x1:.1f} {y1:.1f}" '
                     f'stroke="{cor}" stroke-width="26" fill="none"/>')
    rotulos = []
    for v in (0, 20, 40, 60, 80, 100):
        x, y = ponto(v, R + 24)
        rotulos.append(f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" '
                       f'fill="{TXT_CINZA}" font-family="Arial" font-size="12">{v}</text>')
    xp, yp = ponto(max(2, min(98, val)), R - 24)
    ponteiro = (f'<line x1="{cx}" y1="{cy}" x2="{xp:.1f}" y2="{yp:.1f}" '
                f'stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
                f'<circle cx="{cx}" cy="{cy}" r="7" fill="white" stroke="{NAVY}" '
                f'stroke-width="4"/>')
    svg = "".join(arcos) + "".join(rotulos) + ponteiro
    estagio_hex = p.get("estagio_hex", VERDE)

    return html.Div(style={"background": CARTAO_BRANCO, "borderRadius": "16px",
                           "boxShadow": SOMBRA, "padding": "22px 24px",
                           "width": "300px", "flexShrink": "0",
                           "textAlign": "center", "display": "flex",
                           "flexDirection": "column",
                           "justifyContent": "center"},
                    children=[
        html.Div("TERMÔMETRO DO", style={"color": NAVY, "fontWeight": "700",
                                          "fontSize": "16px", "letterSpacing": "0.5px"}),
        html.Div("CICLO ECONÔMICO", style={"color": NAVY, "fontWeight": "700",
                                            "fontSize": "16px", "letterSpacing": "0.5px",
                                            "marginBottom": "8px"}),
        html.Img(src=_svg_uri(svg, 260, 160),
                 style={"width": "260px", "height": "160px"}),
        html.Div(f"{val:.0f}%".replace(".", ","),
                 style={"fontSize": "40px", "fontWeight": "700",
                        "color": estagio_hex, "lineHeight": "1.1"}),
        html.Div([html.Span(p.get("estagio_rotulo", "—"), style={
            "background": estagio_hex, "color": "white", "borderRadius": "16px",
            "padding": "4px 14px", "fontSize": "12px", "fontWeight": "700",
            "letterSpacing": "0.5px"})], style={"margin": "8px 0 6px"}),
        html.Div(f"Difusão positiva do núcleo · ref. {_mes_pt(p['referencia_alvo'])}",
                 style={"fontSize": "12px", "color": NAVY, "fontWeight": "600"}),
        html.Div("% dos indicadores centrais em expansão",
                 style={"fontSize": "11px", "color": TXT_CINZA, "marginTop": "2px"}),
    ])


# ---------------------------------------------------------------- cartões
def _valor_destaque(ind):
    """Número grande do cartão + legenda, conforme o tipo da série.

    O número grande acompanha a TENDÊNCIA (MM3M vs 3 meses anteriores) —
    a mesma métrica que define a cor do cartão — para que cor e número
    contem sempre a mesma história. O mês isolado vira linha secundária.
    """
    t = ind.get("tipo", "indice")
    if t == "taxa":
        return (_fmt_num(ind["nivel"], 1) + "%",
                "Taxa no trimestre móvel (subir é piora)")
    if t == "fluxo":
        v = ind.get("nivel")
        corpo = "—" if v is None else ("+" if v >= 0 else "−") + f"{abs(v):,.0f}".replace(",", ".")
        return corpo, "Saldo do mês: admissões − desligamentos"
    sufixo = " (dessaz.)" if ind["chave"].startswith(
        ("ibcbr", "pib", "pim", "pmc", "pms")) else ""
    return (_fmt_var(ind.get("var_mm3_3m"), "%"),
            f"Tendência de 3 meses{sufixo} · mês: "
            f"{_fmt_var(ind.get('var_mensal'), '%')}")


def _cartao(titulo, valor, ref, legenda, status, id_clique, spark=None, subtitulo=None):
    filhos = [
        html.Div([
            html.Div([
                html.Div(titulo, style={"fontSize": "24px", "fontWeight": "700",
                                        "lineHeight": "1.15"}),
                (html.Div(subtitulo, style={"fontSize": "12px", "opacity": "0.85",
                                            "marginTop": "3px"}) if subtitulo else None),
            ], style={"flex": "1", "minWidth": "0"}),
            _seta_icone(status["ang"]),
        ], style={"display": "flex", "alignItems": "flex-start", "gap": "10px"}),
        html.Div(valor, style={"fontSize": "38px", "fontWeight": "700",
                               "margin": "12px 0 2px"}),
        html.Div(_mes_pt(ref), style={"fontSize": "15px", "fontWeight": "600"}),
        html.Div(legenda, style={"fontSize": "12px", "opacity": "0.9",
                                 "marginTop": "3px"}),
    ]
    if spark is not None:
        filhos.append(spark)
    return html.Button(id=id_clique, n_clicks=0, children=filhos, style={
        "background": status["hex"], "color": "white", "border": "none",
        "borderRadius": "16px", "padding": "20px 22px", "width": "100%",
        "minHeight": "280px", "display": "flex", "flexDirection": "column",
        "alignItems": "stretch", "textAlign": "left", "cursor": "pointer",
        "boxShadow": SOMBRA, "fontFamily": F_CORPO})


def _cartao_setor(setor, p):
    grupo = [i for i in p["indicadores"] if i["dimensao"] in setor["dims"]]
    status = _status_setor(grupo)
    destaque = next((i for i in grupo if i["nucleo"]), grupo[0])
    valor, _ = _valor_destaque(destaque)
    n_verde = _conta_altas(grupo)
    legenda = f"{destaque['rotulo']} · {n_verde} de {len(grupo)} indicadores em alta"
    return _cartao(f"{setor['icone']} {setor['nome']}", valor,
                   destaque["referencia"], legenda, status,
                   {"type": "setor", "index": setor["slug"]},
                   spark=_spark_branca(destaque["serie"]))


def _cartao_indicador(ind):
    status = _status_ind(ind)
    valor, legenda = _valor_destaque(ind)
    return _cartao(ind["rotulo"], valor, ind["referencia"], legenda, status,
                   {"type": "card", "index": ind["chave"]},
                   spark=_spark_branca(ind["serie"]),
                   subtitulo=status["rotulo"])


# ---------------------------------------------------------------- cabeçalho
def _abas():
    base = {"display": "flex", "alignItems": "center", "gap": "8px",
            "borderRadius": "24px", "padding": "10px 22px", "fontSize": "13px",
            "fontWeight": "700", "letterSpacing": "0.5px", "fontFamily": F_CORPO}
    ativa = {**base, "background": NAVY, "color": "white", "border": "none",
             "cursor": "default", "boxShadow": SOMBRA}
    inativa = {**base, "background": CARTAO_BRANCO, "color": "#9aa3b2",
               "border": "1px solid #dde1ea", "cursor": "not-allowed"}
    return html.Div([
        html.Button("🕐 ANTECEDENTES", style=inativa, disabled=True,
                    title="Tópico 2 — em construção"),
        html.Button("📊 COINCIDENTES", style=ativa),
        html.Button("⏳ DEFASADOS", style=inativa, disabled=True,
                    title="Tópico 3 — em construção"),
    ], style={"display": "flex", "gap": "12px", "margin": "18px 0 22px"})


def _cabecalho():
    return html.Div([
        html.Div([
            html.Div("INDICADORES", style={
                "fontFamily": F_TITULO, "fontSize": "42px", "fontWeight": "700",
                "color": NAVY, "lineHeight": "1.05"}),
            html.Div("PANORAMA MACROECONÔMICO — CICLO DE NEGÓCIOS", style={
                "fontSize": "13px", "color": "#8b93a5", "letterSpacing": "2.5px",
                "marginTop": "4px"}),
            html.Div(style={"width": "110px", "height": "3px", "background": NAVY,
                            "marginTop": "10px", "borderRadius": "2px"}),
        ]),
        html.Button("⟳ Atualizar dados", id="btn-refresh", n_clicks=0, style={
            "background": CARTAO_BRANCO, "color": NAVY, "fontWeight": "600",
            "border": "1px solid #dde1ea", "borderRadius": "10px",
            "padding": "10px 16px", "cursor": "pointer", "boxShadow": SOMBRA,
            "fontFamily": F_CORPO}),
    ], style={"display": "flex", "justifyContent": "space-between",
              "alignItems": "flex-start"})


def _rodape(p):
    return html.Div([
        html.Span("ⓘ ", style={"color": NAVY, "fontWeight": "700"}),
        html.Span("Variações em relação ao período anterior. ",
                  style={"color": TXT_CINZA}),
        html.Span("Fonte: ", style={"fontWeight": "700", "color": NAVY}),
        html.Span("Banco Central (SGS) e IBGE (SIDRA). ", style={"color": TXT_CINZA}),
        html.Span("Atualizado em: ", style={"fontWeight": "700", "color": NAVY}),
        html.Span(p["gerado_em"] + ". Leitura qualitativa — não é datação oficial.",
                  style={"color": TXT_CINZA}),
    ], style={"fontSize": "12px", "marginTop": "26px"})


def _botao_voltar(idx, texto):
    return html.Button(f"←  {texto}", id={"type": "voltar", "index": idx}, n_clicks=0,
                       style={"background": "transparent", "border": "none",
                              "color": "white", "fontSize": "16px",
                              "fontWeight": "700", "cursor": "pointer",
                              "fontFamily": F_CORPO, "padding": "0"})


# ---------------------------------------------------------------- telas
def _tela_home(p):
    cards = [_cartao_setor(s, p) for s in SETORES]
    return html.Div([
        html.Div(cards, style={"display": "grid",
                               "gridTemplateColumns": "repeat(3, minmax(260px, 1fr))",
                               "gap": "18px", "flex": "1", "minWidth": "0"}),
        _termometro(p),
    ], style={"display": "flex", "gap": "18px", "alignItems": "stretch"})


def _tela_setor(p, slug):
    setor = _setor_por_slug(slug) or SETORES[0]
    grupo = [i for i in p["indicadores"] if i["dimensao"] in setor["dims"]]
    status = _status_setor(grupo)
    barra = html.Div([
        _botao_voltar("home", ""),
        html.Span(f"{setor['icone']}  Termômetro — {setor['nome']}",
                  style={"fontSize": "22px", "fontWeight": "700", "color": "white",
                         "marginLeft": "6px"}),
    ], style={"background": status["hex"], "borderRadius": "14px",
              "padding": "14px 20px", "display": "flex", "alignItems": "center",
              "marginBottom": "18px", "boxShadow": SOMBRA})
    cards = [_cartao_indicador(i) for i in grupo]
    return html.Div([barra,
                     html.Div(cards, style={"display": "grid",
                                            "gridTemplateColumns": "repeat(3, minmax(260px, 1fr))",
                                            "gap": "18px"})])


def _fig_serie_completa(ind, status):
    s = ind["serie"]
    datas, vals = s["datas"], s["valores"]
    # intervalo típico: média ± 1 desvio dos últimos 5 anos
    ult = [v for v in vals[-60:] if v is not None]
    media = sum(ult) / len(ult) if ult else 0
    dp = math.sqrt(sum((v - media) ** 2 for v in ult) / len(ult)) if ult else 0

    fig = go.Figure()
    fig.add_hrect(y0=media - dp, y1=media + dp, fillcolor=status["hex"],
                  opacity=0.10, line_width=0)
    fig.add_hline(y=media, line=dict(color=status["hex"], width=1, dash="dot"),
                  opacity=0.6)
    fig.add_trace(go.Scatter(x=datas, y=vals, mode="lines", name="Série",
                             line=dict(color=status["hex"], width=2.4)))
    fig.add_trace(go.Scatter(x=datas, y=s["mm3"], mode="lines", name="Média móvel 3m",
                             line=dict(color=NAVY, width=1.4, dash="dash")))
    if vals:
        fig.add_annotation(x=datas[-1], y=vals[-1],
                           text=f"<b>{_fmt_num(vals[-1], 1)}</b>",
                           showarrow=True, arrowhead=0, ax=42, ay=-26,
                           font=dict(color="white", size=13),
                           bgcolor=status["hex"], borderpad=5)
    mm3_fim = next(((d, v) for d, v in zip(reversed(datas), reversed(s["mm3"]))
                    if v is not None), None)
    if mm3_fim:
        fig.add_annotation(x=mm3_fim[0], y=mm3_fim[1],
                           text=f"<b>{_fmt_num(mm3_fim[1], 1)}</b>",
                           showarrow=True, arrowhead=0, ax=42, ay=22,
                           font=dict(color="white", size=13),
                           bgcolor=NAVY, borderpad=5)
    fig.update_layout(
        height=420, margin=dict(l=46, r=24, t=28, b=36),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=F_CORPO, color=TXT_CINZA),
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(gridcolor="#eceff5", rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(gridcolor="#eceff5"))
    return fig


def _fig_12m(ind, status):
    s = ind["serie"]
    datas, vals = s["datas"][-12:], s["valores"][-12:]
    mm3 = s["mm3"][-12:]
    fig = go.Figure(go.Scatter(x=datas, y=vals, mode="lines+markers",
                               name="Série",
                               line=dict(color=status["hex"], width=2.4),
                               marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=datas, y=mm3, mode="lines", name="Média móvel 3m",
                             line=dict(color=NAVY, width=1.4, dash="dash")))
    if vals and vals[-1] is not None:
        fig.add_annotation(x=datas[-1], y=vals[-1],
                           text=f"<b>{_fmt_num(vals[-1], 1)}</b>",
                           showarrow=True, arrowhead=0, ax=-34, ay=-20,
                           font=dict(color="white", size=11),
                           bgcolor=status["hex"], borderpad=4)
    mm3_fim = next(((d, v) for d, v in zip(reversed(datas), reversed(mm3))
                    if v is not None), None)
    if mm3_fim:
        fig.add_annotation(x=mm3_fim[0], y=mm3_fim[1],
                           text=f"<b>{_fmt_num(mm3_fim[1], 1)}</b>",
                           showarrow=True, arrowhead=0, ax=-34, ay=20,
                           font=dict(color="white", size=11),
                           bgcolor=NAVY, borderpad=4)
    fig.update_layout(height=240, margin=dict(l=40, r=14, t=10, b=30),
                      paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family=F_CORPO, color=TXT_CINZA, size=11),
                      xaxis=dict(gridcolor="#eceff5"),
                      yaxis=dict(gridcolor="#eceff5"), showlegend=False)
    return fig


def _ficha(icone, titulo, texto, cor):
    return html.Div([
        html.Div([html.Span(icone + "  ", style={"fontSize": "17px"}),
                  html.Span(titulo, style={"fontWeight": "700", "color": cor,
                                           "fontSize": "15px"})],
                 style={"marginBottom": "8px"}),
        html.Div(texto, style={"fontSize": "13px", "color": "#4b5563",
                               "lineHeight": "1.6"}),
    ], style={"background": CARTAO_BRANCO, "borderRadius": "14px", "padding": "18px",
              "flex": "1", "minWidth": "240px", "boxShadow": SOMBRA})


def _caixa_metrica(numero, titulo, valor, descricao, cor_valor):
    return html.Div([
        html.Div(f"MÉTRICA {numero}", style={"fontSize": "11px", "fontWeight": "700",
                                             "color": TXT_CINZA,
                                             "letterSpacing": "1px"}),
        html.Div(titulo, style={"fontSize": "14px", "fontWeight": "700",
                                "color": NAVY, "marginTop": "2px"}),
        html.Div(valor, style={"fontSize": "28px", "fontWeight": "700",
                               "color": cor_valor, "margin": "6px 0 2px"}),
        html.Div(descricao, style={"fontSize": "12px", "color": TXT_CINZA,
                                   "lineHeight": "1.4"}),
    ], style={"background": CARTAO_BRANCO, "borderRadius": "14px",
              "padding": "14px 18px", "flex": "1", "minWidth": "220px",
              "boxShadow": SOMBRA})


def _faixa_metricas(ind, status):
    """As três métricas das Orientações, lado a lado, na página de detalhe."""
    t = ind.get("tipo", "indice")
    u = ind.get("unidade", "%")
    if t == "taxa":
        d1 = "Diferença da taxa sobre o período anterior, em pontos percentuais."
        d3 = "Diferença da MM3M atual contra a dos 3 meses anteriores (p.p.)."
    elif t == "fluxo":
        d1 = "Variação do nível sobre o mês anterior (o saldo pode cruzar zero)."
        d3 = "Diferença da MM3M atual contra a dos 3 meses anteriores (nível)."
    else:
        d1 = "Variação percentual dessazonalizada sobre o mês anterior."
        d3 = "Variação % da MM3M atual contra a dos 3 meses anteriores."
    v1 = _fmt_var(ind.get("var_mensal"), u)
    v2 = _fmt_num(ind.get("mm3"), 1)
    v3 = _fmt_var(ind.get("var_mm3_3m"), u)
    return html.Div([
        _caixa_metrica(1, "Variação no mês", v1, d1, NAVY),
        _caixa_metrica(2, "Média móvel de 3 meses", v2,
                       "Média do nível dos últimos 3 meses — suaviza oscilações "
                       "pontuais da série.", NAVY),
        _caixa_metrica(3, "Tendência (MM3M vs. 3 meses)", v3,
                       d3 + " É a métrica que define a cor do indicador.",
                       status["hex"]),
    ], style={"display": "flex", "gap": "14px", "flexWrap": "wrap",
              "marginBottom": "14px"})


def _tela_detalhe(p, chave, slug):
    indby = {i["chave"]: i for i in p["indicadores"]}
    ind = indby.get(chave) or p["indicadores"][0]
    setor = _setor_por_slug(slug)
    if setor is None:
        setor = next((s for s in SETORES if ind["dimensao"] in s["dims"]), SETORES[0])
    status = _status_ind(ind)
    irmaos = [i for i in p["indicadores"] if i["dimensao"] in setor["dims"]]

    barra = html.Div([
        _botao_voltar(setor["slug"], ""),
        html.Span(f"Termômetro — {setor['nome']}",
                  style={"fontSize": "22px", "fontWeight": "700", "color": "white",
                         "marginLeft": "6px"}),
    ], style={"background": status["hex"], "borderRadius": "14px",
              "padding": "14px 20px", "display": "flex", "alignItems": "center",
              "marginBottom": "14px", "boxShadow": SOMBRA})

    # tira de navegação entre os indicadores do setor
    pills = []
    for i in irmaos:
        st_i = _status_ind(i)
        atual = i["chave"] == ind["chave"]
        pills.append(html.Button([
            html.Span("● ", style={"color": st_i["hex"]}),
            html.Span(i["rotulo"], style={"whiteSpace": "nowrap"}),
        ], id={"type": "strip", "index": i["chave"]}, n_clicks=0, style={
            "background": CARTAO_BRANCO if not atual else st_i["hex"],
            "color": "#374151" if not atual else "white",
            "border": "1px solid #e2e6ee", "borderRadius": "20px",
            "padding": "7px 14px", "fontSize": "12px", "fontWeight": "600",
            "cursor": "pointer", "fontFamily": F_CORPO, "boxShadow": SOMBRA}))
    tira = html.Div(pills, style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                                  "marginBottom": "18px"})

    s = ind["serie"]
    meta = html.Div([
        html.Div([
            html.Div(ind["rotulo"], style={"fontSize": "28px", "fontWeight": "700",
                                           "color": status["hex"]}),
            html.Div(f"sinal atual: {status['rotulo']} · "
                     f"mês {_fmt_var(ind['var_mensal'], ind['unidade'])} · "
                     f"MM3M {_fmt_var(ind['var_mm3_3m'], ind['unidade'])}",
                     style={"fontSize": "13px", "color": TXT_CINZA, "marginTop": "4px"}),
        ], style={"flex": "1"}),
        html.Div([
            html.Div(f"VALORES DE {_mes_pt(s['datas'][0]).upper()} A "
                     f"{_mes_pt(s['datas'][-1]).upper()}" if s["datas"] else "—",
                     style={"fontSize": "11px", "color": TXT_CINZA,
                            "letterSpacing": "0.5px"}),
            html.Div(f"FONTE: {ind['fonte_desc']}",
                     style={"fontSize": "11px", "color": TXT_CINZA,
                            "letterSpacing": "0.5px", "marginTop": "4px"}),
            html.Div(f"Atualizado em {p['gerado_em']}",
                     style={"fontSize": "11px", "color": TXT_CINZA, "marginTop": "4px"}),
        ], style={"textAlign": "right"}),
    ], style={"display": "flex", "alignItems": "flex-start", "gap": "16px",
              "margin": "2px 4px 12px"})

    metricas3 = _faixa_metricas(ind, status)

    grafico = html.Div(dcc.Graph(figure=_fig_serie_completa(ind, status),
                                 config={"displayModeBar": False}),
                       style={"background": CARTAO_BRANCO, "borderRadius": "14px",
                              "padding": "10px", "flex": "2.2", "minWidth": "420px",
                              "boxShadow": SOMBRA})
    painel12 = html.Div([
        html.Div("Últimos 12 meses", style={"fontWeight": "700", "color": NAVY,
                                            "fontSize": "15px",
                                            "margin": "8px 8px 0"}),
        dcc.Graph(figure=_fig_12m(ind, status), config={"displayModeBar": False}),
        html.Div([
            html.Div([html.Div("Nível atual", style={"fontSize": "11px",
                                                     "color": TXT_CINZA}),
                      html.Div(_fmt_num(ind["nivel"], 1),
                               style={"fontSize": "20px", "fontWeight": "700",
                                      "color": status["hex"]})]),
            html.Div([html.Div("MM3M", style={"fontSize": "11px",
                                              "color": TXT_CINZA}),
                      html.Div(_fmt_num(ind["mm3"], 1),
                               style={"fontSize": "20px", "fontWeight": "700",
                                      "color": NAVY})]),
        ], style={"display": "flex", "justifyContent": "space-around",
                  "padding": "4px 8px 12px"}),
    ], style={"background": CARTAO_BRANCO, "borderRadius": "14px", "flex": "1",
              "minWidth": "260px", "boxShadow": SOMBRA})

    txt = TEXTOS.get(ind["chave"], {})
    fichas_titulo = html.Div(f"SAIBA MAIS SOBRE O INDICADOR",
                             style={"fontWeight": "700", "color": status["hex"],
                                    "letterSpacing": "1px", "fontSize": "13px",
                                    "margin": "20px 4px 10px"})
    fichas = html.Div([
        _ficha("ⓘ", "O que é?", txt.get("o_que", "—"), status["hex"]),
        _ficha("🎯", "Por que é importante?", txt.get("por_que", "—"), status["hex"]),
        _ficha("🔎", "Como interpretar?", txt.get("como", "—"), status["hex"]),
    ], style={"display": "flex", "gap": "14px", "flexWrap": "wrap"})

    return html.Div([barra, tira, meta, metricas3,
                     html.Div([grafico, painel12],
                              style={"display": "flex", "gap": "14px",
                                     "flexWrap": "wrap"}),
                     fichas_titulo, fichas])


# ---------------------------------------------------------------- app
app = Dash(__name__, external_scripts=[CDN_PLOTLY],
           external_stylesheets=FONTES_CSS,
           suppress_callback_exceptions=True,
           title="Indicadores — Panorama Macroeconômico")
server = app.server

_PAYLOAD_INICIAL = painel_dados.montar_payload(usar_cache=True)


def _layout():
    return html.Div(style={"background": BG, "minHeight": "100vh",
                           "padding": "26px 34px", "fontFamily": F_CORPO},
                    children=[
        dcc.Store(id="payload", data=_PAYLOAD_INICIAL),
        dcc.Store(id="view", data={"tela": "home"}),
        _cabecalho(),
        _abas(),
        html.Div(id="conteudo"),
        html.Div(id="rodape"),
    ])


app.layout = _layout


@app.callback(Output("conteudo", "children"), Output("rodape", "children"),
              Input("view", "data"), Input("payload", "data"))
def _render(view, p):
    tela = (view or {}).get("tela", "home")
    if tela == "setor":
        corpo = _tela_setor(p, view.get("setor"))
    elif tela == "detalhe":
        corpo = _tela_detalhe(p, view.get("indicador"), view.get("setor"))
    else:
        corpo = _tela_home(p)
    return corpo, _rodape(p)


@app.callback(Output("view", "data"),
              Input({"type": "setor", "index": ALL}, "n_clicks"),
              Input({"type": "card", "index": ALL}, "n_clicks"),
              Input({"type": "strip", "index": ALL}, "n_clicks"),
              Input({"type": "voltar", "index": ALL}, "n_clicks"),
              State("view", "data"),
              prevent_initial_call=True)
def _navegar(_s, _c, _t, _v, view):
    trig = ctx.triggered_id
    if not isinstance(trig, dict) or not ctx.triggered[0]["value"]:
        raise PreventUpdate
    tipo, idx = trig["type"], trig["index"]
    view = view or {}
    if tipo == "setor":
        return {"tela": "setor", "setor": idx}
    if tipo in ("card", "strip"):
        return {"tela": "detalhe", "setor": view.get("setor"), "indicador": idx}
    if tipo == "voltar":
        if idx == "home":
            return {"tela": "home"}
        return {"tela": "setor", "setor": idx}
    raise PreventUpdate


@app.callback(Output("payload", "data"), Input("btn-refresh", "n_clicks"),
              prevent_initial_call=True)
def _refresh(_n):
    return painel_dados.montar_payload(usar_cache=False)


def main():
    print("Dashboard em http://127.0.0.1:8050  (Ctrl+C para encerrar)")
    app.run(debug=False, port=8050)


if __name__ == "__main__":
    main()
