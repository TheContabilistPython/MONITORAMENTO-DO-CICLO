# -*- coding: utf-8 -*-
"""
Dashboard visual do Painel do Ciclo Econômico — estilo "cockpit de avião".

Leitura em 3 camadas:
  1. ESTÁGIO + RUMO   -> para onde a economia está indo (horizonte artificial)
  2. INSTRUMENTOS     -> ícones grandes com "pílulas" de status coloridas
                         (inspirado em painéis de monitoramento de datacenter)
  3. RADAR            -> clique em qualquer instrumento para abrir a série

Rodar:
    python -m painel_ciclo.dashboard
    # abra http://127.0.0.1:8050 no navegador
"""
from urllib.parse import quote

import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, ALL, ctx

from . import painel_dados

# ---------------------------------------------------------------- paleta cockpit
BG = "#0a0e15"          # fundo geral (quase preto, azul-aviação)
PANEL = "#131a26"       # cartões
PANEL2 = "#1b2536"      # realce / botões
TXT = "#eef3fa"         # texto principal
TXT_DIM = "#7e93b3"     # texto secundário
BORDA = "#243650"

VERDE = "#2e9e4f"
AMARELO = "#e8c12a"
LARANJA = "#e8821a"
VERMELHO = "#d8362a"
ROXO = "#7a3ea8"

CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"
FONTE = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"


# ---------------------------------------------------------------- formatação
def _fmt_num(v):
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}".replace(",", ".")
    if a >= 100:
        return f"{v:,.1f}".replace(",", ".")
    return f"{v:.2f}".replace(".", ",")


def _fmt_var(v, unidade):
    if v is None:
        return "—"
    sinal = "+" if v >= 0 else "−"
    a = abs(v)
    if unidade == "%":
        corpo = f"{a:.2f}".replace(".", ",") + "%"
    elif unidade == "p.p.":
        corpo = f"{a:.2f}".replace(".", ",") + " p.p."
    else:  # nível (fluxo)
        corpo = f"{a:,.0f}".replace(",", ".")
    return f"{sinal}{corpo}"


def _texto_sobre(cor_hex):
    """Escolhe texto escuro ou claro conforme a luminância do fundo."""
    try:
        r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return "#0a0e15" if lum > 140 else "#ffffff"
    except Exception:
        return "#ffffff"


# ---------------------------------------------------------------- ícones (SVG)
def _svg_uri(corpo, vb="0 0 24 24"):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" fill="none" '
           f'stroke="{TXT}" stroke-width="1.4" stroke-linecap="round" '
           f'stroke-linejoin="round">{corpo}</svg>')
    return "data:image/svg+xml;utf8," + quote(svg)


_ICONES = {
    "pulso": '<polyline points="2 12 6 12 9 5 13 19 16 12 22 12"/>',
    "barras": ('<line x1="4" y1="20" x2="20" y2="20"/>'
               '<rect x="5" y="12" width="3.5" height="8"/>'
               '<rect x="10.2" y="8" width="3.5" height="12"/>'
               '<rect x="15.5" y="4" width="3.5" height="16"/>'),
    "fabrica": ('<path d="M3 20h18"/><path d="M4 20V10l5 3v-3l5 3v-3l5 3v7"/>'
                '<path d="M7 7V4h3v4"/>'),
    "carrinho": ('<circle cx="9" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>'
                 '<path d="M3 4h2.5l2.2 11h10.1l2.2-8H6"/>'),
    "maleta": ('<rect x="3" y="8" width="18" height="12" rx="2"/>'
               '<path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>'
               '<path d="M3 13h18"/>'),
    "pessoas": ('<circle cx="9" cy="8" r="3"/><path d="M3.5 20c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/>'
                '<circle cx="17" cy="9" r="2.3"/><path d="M16 15c2.8 0 4.8 1.8 4.8 4.5"/>'),
    "cracha": ('<rect x="5" y="4" width="14" height="17" rx="2"/>'
               '<path d="M10 4V2.5h4V4"/><circle cx="12" cy="10" r="2.2"/>'
               '<path d="M8.5 17c0-2 1.6-3.2 3.5-3.2s3.5 1.2 3.5 3.2"/>'),
    "moedas": ('<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v9"/>'
               '<path d="M14.8 9.2c-.6-1-1.6-1.4-2.8-1.4-1.5 0-2.7.8-2.7 2.1 0 2.9 5.6 1.5 5.6 4.3 '
               '0 1.3-1.3 2.1-2.9 2.2-1.3 0-2.4-.5-3-1.5"/>'),
    "velocimetro": ('<path d="M4 18a9 9 0 1 1 16 0"/><line x1="12" y1="15" x2="16.5" y2="9.5"/>'
                    '<circle cx="12" cy="15" r="1.2"/>'),
}

_REGRAS_ICONE = [
    (("ibc", "atividade"), "pulso"),
    (("pib",), "barras"),
    (("indús", "indus", "pim", "produção", "producao"), "fabrica"),
    (("comérc", "comerc", "varej", "pmc", "veícul", "veicul"), "carrinho"),
    (("serviç", "servic", "pms", "transport"), "maleta"),
    (("pnad", "ocupa", "desocup", "trabalho", "subutil"), "pessoas"),
    (("caged", "formal", "admiss", "deslig", "saldo", "víncul", "vincul"), "cracha"),
    (("rend", "massa"), "moedas"),
]


def _icone(ind):
    alvo = f"{ind.get('chave','')} {ind.get('rotulo','')} {ind.get('dimensao','')}".lower()
    nome = "velocimetro"
    for chaves, ic in _REGRAS_ICONE:
        if any(k in alvo for k in chaves):
            nome = ic
            break
    return html.Img(src=_svg_uri(_ICONES[nome]),
                    style={"width": "52px", "height": "52px", "opacity": "0.92"})


# ---------------------------------------------------------------- instrumentos
def _sparkline(ind):
    s = ind["serie"]
    n = min(len(s["valores"]), 36)
    fig = go.Figure(go.Scatter(x=s["datas"][-n:], y=s["valores"][-n:], mode="lines",
                               line=dict(color=ind["cor_hex"], width=1.8),
                               hoverinfo="skip"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=34,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      showlegend=False)
    return dcc.Graph(figure=fig, config={"displayModeBar": False, "staticPlot": True},
                     style={"height": "34px", "marginTop": "8px"})


def _instrumento(ind):
    cor = ind["cor_hex"]
    nucleo_tag = (html.Span("NÚCLEO", style={
        "fontSize": "8px", "letterSpacing": "1px", "color": BG,
        "background": "#5aa9e6", "borderRadius": "3px", "padding": "1px 5px",
        "marginLeft": "6px", "fontWeight": "700"}) if ind["nucleo"] else None)

    return html.Button(
        id={"type": "instr", "index": ind["chave"]}, n_clicks=0,
        title="Clique para abrir a série no radar",
        style={
            "background": "transparent", "border": "none", "cursor": "pointer",
            "width": "190px", "padding": "10px 6px", "color": TXT,
            "fontFamily": FONTE, "borderRadius": "10px",
        },
        children=[
            # rótulo
            html.Div([html.Span(ind["rotulo"],
                                style={"fontSize": "12px", "fontWeight": "600",
                                       "color": TXT}),
                      nucleo_tag],
                     style={"minHeight": "32px", "display": "flex",
                            "alignItems": "center", "justifyContent": "center",
                            "textAlign": "center", "marginBottom": "8px"}),
            # ícone grande (estilo painel de datacenter)
            html.Div(_icone(ind), style={"display": "flex",
                                         "justifyContent": "center",
                                         "marginBottom": "12px"}),
            # pílula de status colorida
            html.Div(_fmt_num(ind["nivel"]), style={
                "background": cor, "color": _texto_sobre(cor),
                "fontSize": "16px", "fontWeight": "800", "padding": "7px 0",
                "borderRadius": "4px", "textAlign": "center",
                "boxShadow": f"0 0 14px {cor}33",
            }),
            # leitura fina
            html.Div(f"ref. {ind['referencia']} · sinal: {ind['sinal_txt']}",
                     style={"fontSize": "9.5px", "color": cor, "textAlign": "center",
                            "marginTop": "6px", "fontWeight": "600"}),
            html.Div([
                html.Span(f"mês {_fmt_var(ind['var_mensal'], ind['unidade'])}",
                          style={"marginRight": "8px"}),
                html.Span(f"MM3M {_fmt_var(ind['var_mm3_3m'], ind['unidade'])}"),
            ], style={"fontSize": "9.5px", "color": TXT_DIM,
                      "textAlign": "center", "marginTop": "2px"}),
            _sparkline(ind),
        ])


def _grade(p):
    secoes = []
    for dim in p["dimensoes"]:
        cards = [_instrumento(i) for i in p["indicadores"] if i["dimensao"] == dim]
        secoes.append(html.Div([
            html.Div(dim.upper(), style={
                "fontSize": "11px", "color": TXT_DIM, "fontWeight": "700",
                "letterSpacing": "2.5px", "textAlign": "center",
                "margin": "18px 0 4px"}),
            html.Div(cards, style={"display": "flex", "flexWrap": "wrap",
                                   "gap": "14px", "justifyContent": "center"}),
        ]))
    return html.Div(secoes, style={
        "background": PANEL, "border": f"1px solid {BORDA}",
        "borderRadius": "14px", "padding": "8px 16px 22px",
    })


# ---------------------------------------------------------------- cockpit (topo)
def _dial_rumo(diag):
    """Horizonte artificial: a seta inclina conforme a difusão positiva."""
    share = diag.get("share_pos")
    share = 0.5 if share is None else max(0.0, min(1.0, share))
    ang = 90 - share * 180  # 100% -> -90° (subindo); 0% -> +90° (caindo)
    if share >= 0.6:
        rotulo, cor = "GANHANDO ALTITUDE", VERDE
    elif share >= 0.4:
        rotulo, cor = "VOO NIVELADO", AMARELO
    else:
        rotulo, cor = "PERDENDO ALTITUDE", VERMELHO

    dial = html.Div(style={
        "width": "150px", "height": "150px", "borderRadius": "50%",
        "border": f"2px solid {BORDA}", "position": "relative",
        "margin": "6px auto", "background":
            f"linear-gradient(to bottom, {VERDE}22 0%, transparent 50%, {VERMELHO}22 100%)",
    }, children=[
        html.Div(style={"position": "absolute", "top": "50%", "left": "8px",
                        "right": "8px", "borderTop": f"1px dashed {TXT_DIM}"}),
        html.Div("➤", style={
            "position": "absolute", "top": "50%", "left": "50%", "color": cor,
            "fontSize": "44px", "lineHeight": "0",
            "transform": f"translate(-50%,-50%) rotate({ang}deg)",
            "transition": "transform .6s ease", "textShadow": f"0 0 16px {cor}88",
        }),
        html.Div("EXPANSÃO", style={"position": "absolute", "top": "10px",
                                    "width": "100%", "textAlign": "center",
                                    "fontSize": "8.5px", "letterSpacing": "1.5px",
                                    "color": VERDE}),
        html.Div("CONTRAÇÃO", style={"position": "absolute", "bottom": "10px",
                                     "width": "100%", "textAlign": "center",
                                     "fontSize": "8.5px", "letterSpacing": "1.5px",
                                     "color": VERMELHO}),
    ])
    return html.Div([
        html.Div("RUMO DA ECONOMIA", style={"fontSize": "11px", "color": TXT_DIM,
                                            "letterSpacing": "2px",
                                            "textAlign": "center"}),
        dial,
        html.Div(rotulo, style={"textAlign": "center", "fontSize": "13px",
                                "fontWeight": "800", "color": cor,
                                "letterSpacing": "1px"}),
        html.Div(f"{share*100:.0f}% dos indicadores de núcleo em alta",
                 style={"textAlign": "center", "fontSize": "10px",
                        "color": TXT_DIM, "marginTop": "2px"}),
    ], style={"flex": "0 0 230px", "background": PANEL, "borderRadius": "14px",
              "padding": "14px", "border": f"1px solid {BORDA}"})


def _gauge(valor, faixa, passos, sufixo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
        number={"font": {"size": 28, "color": TXT}, "suffix": sufixo},
        gauge={
            "axis": {"range": faixa, "tickcolor": TXT_DIM,
                     "tickfont": {"color": TXT_DIM, "size": 9}},
            "bar": {"color": "rgba(255,255,255,0.9)", "thickness": 0.16},
            "borderwidth": 0,
            "steps": passos,
        }))
    fig.update_layout(height=150, margin=dict(l=18, r=18, t=8, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": TXT})
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _cockpit(p):
    diag = p["diag"]
    ct = diag.get("ct")
    share = (diag.get("share_pos") or 0) * 100

    status = html.Div([
        html.Div("ESTÁGIO DO CICLO · BLOCO COINCIDENTE",
                 style={"fontSize": "10.5px", "letterSpacing": "2px",
                        "color": "rgba(255,255,255,0.85)"}),
        html.Div(p["estagio_rotulo"],
                 style={"fontSize": "40px", "fontWeight": "900", "color": "#fff",
                        "lineHeight": "1.05", "margin": "8px 0",
                        "textShadow": "0 1px 10px rgba(0,0,0,0.35)"}),
        html.Div(f"Ct = {ct}  ·  difusão positiva {share:.0f}%  ·  "
                 f"{diag.get('n_pos', '?')} subindo / {diag.get('n_neg', '?')} caindo",
                 style={"fontSize": "13px", "color": "#f2f6fc"}),
        html.Div(f"Fechamento {p['fechamento']} · alvo {p['referencia_alvo']} · "
                 f"gerado em {p['gerado_em']}",
                 style={"fontSize": "10.5px", "color": "rgba(255,255,255,0.75)",
                        "marginTop": "10px"}),
    ], style={"flex": "1.5", "minWidth": "300px", "background": p["estagio_hex"],
              "borderRadius": "14px", "padding": "20px 24px",
              "boxShadow": f"0 0 30px {p['estagio_hex']}44"})

    g1 = html.Div([
        html.Div("PONTUAÇÃO Ct", style={"fontSize": "10.5px", "color": TXT_DIM,
                                        "letterSpacing": "2px",
                                        "textAlign": "center"}),
        _gauge(ct if ct is not None else 0, [0, 2],
               [{"range": [0, 0.67], "color": VERDE},
                {"range": [0.67, 1.33], "color": AMARELO},
                {"range": [1.33, 2], "color": VERMELHO}], " / 2"),
        html.Div("0 favorável · 1 misto · 2 deterioração",
                 style={"fontSize": "9.5px", "color": TXT_DIM,
                        "textAlign": "center"}),
    ], style={"flex": "1", "minWidth": "210px", "background": PANEL,
              "borderRadius": "14px", "padding": "14px",
              "border": f"1px solid {BORDA}"})

    g2 = html.Div([
        html.Div("DIFUSÃO POSITIVA", style={"fontSize": "10.5px", "color": TXT_DIM,
                                            "letterSpacing": "2px",
                                            "textAlign": "center"}),
        _gauge(share, [0, 100],
               [{"range": [0, 40], "color": VERMELHO},
                {"range": [40, 60], "color": AMARELO},
                {"range": [60, 100], "color": VERDE}], "%"),
        html.Div("% de indicadores de núcleo crescendo",
                 style={"fontSize": "9.5px", "color": TXT_DIM,
                        "textAlign": "center"}),
    ], style={"flex": "1", "minWidth": "210px", "background": PANEL,
              "borderRadius": "14px", "padding": "14px",
              "border": f"1px solid {BORDA}"})

    return html.Div([status, _dial_rumo(diag), g1, g2],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap",
                           "marginBottom": "16px"})


def _escala_legenda():
    itens = [("EXPANSÃO", VERDE), ("DESACELERAÇÃO", AMARELO), ("ALERTA", LARANJA),
             ("RECESSÃO", VERMELHO), ("CONTRAÇÃO", ROXO)]
    chips = [html.Span(nome, style={
        "background": cor, "color": _texto_sobre(cor), "padding": "3px 11px",
        "borderRadius": "20px", "fontSize": "10.5px", "fontWeight": "700",
        "marginRight": "8px", "letterSpacing": "0.5px"}) for nome, cor in itens]
    return html.Div([
        html.Span("Escala de alerta (Et 0–8): ",
                  style={"color": TXT_DIM, "fontSize": "11px",
                         "marginRight": "8px"}),
        *chips,
        html.Span(" — hoje só o bloco coincidente (1 de 4) está implementado.",
                  style={"color": TXT_DIM, "fontSize": "11px"}),
    ], style={"margin": "4px 0 16px"})


# ---------------------------------------------------------------- radar (série)
def _figura_serie(ind):
    s = ind["serie"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["datas"], y=s["valores"], mode="lines",
                             name="Nível",
                             line=dict(color=ind["cor_hex"], width=2.2),
                             fill="tozeroy",
                             fillcolor=f"rgba(255,255,255,0.03)"))
    fig.add_trace(go.Scatter(x=s["datas"], y=s["mm3"], mode="lines", name="MM3M",
                             line=dict(color="#ffffff", width=1.3, dash="dash")))
    fig.update_layout(
        height=420, margin=dict(l=50, r=20, t=52, b=40),
        title=dict(text=f"RADAR · {ind['rotulo']} (ref. {ind['referencia']})",
                   font={"color": TXT, "size": 15}),
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TXT_DIM},
        legend=dict(orientation="h", y=1.08, x=0, font={"color": TXT}),
        xaxis=dict(gridcolor=BORDA, rangeslider=dict(visible=True, thickness=0.06)),
        yaxis=dict(gridcolor=BORDA))
    return fig


# ---------------------------------------------------------------- app
app = Dash(__name__, external_scripts=[CDN_PLOTLY],
           title="Painel do Ciclo Econômico")
server = app.server

_PAYLOAD_INICIAL = painel_dados.montar_payload(usar_cache=True)


def _layout():
    return html.Div(style={"background": BG, "minHeight": "100vh",
                           "padding": "20px 28px", "fontFamily": FONTE},
                    children=[
        dcc.Store(id="payload", data=_PAYLOAD_INICIAL),
        dcc.Interval(id="tick", interval=1000),

        # barra superior: título + relógio (como no painel de referência)
        html.Div([
            html.Div([
                html.Span("✈ ", style={"fontSize": "20px"}),
                html.Span("PAINEL DO CICLO ECONÔMICO",
                          style={"fontSize": "19px", "fontWeight": "800",
                                 "color": TXT, "letterSpacing": "2px"}),
            ]),
            html.Div([
                html.Div(id="relogio-data",
                         style={"fontSize": "10px", "color": TXT_DIM,
                                "textAlign": "right"}),
                html.Div(id="relogio-hora",
                         style={"fontSize": "22px", "fontWeight": "800",
                                "color": TXT, "lineHeight": "1",
                                "fontVariantNumeric": "tabular-nums"}),
            ]),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "marginBottom": "14px"}),

        _escala_legenda(),
        html.Div(id="cockpit"),

        html.Div([
            html.Div("INSTRUMENTOS · clique em um indicador para abrir o radar",
                     style={"fontSize": "11px", "color": TXT_DIM,
                            "fontWeight": "700", "letterSpacing": "2px"}),
            html.Button("⟳ ATUALIZAR DADOS (AO VIVO)", id="btn-refresh", n_clicks=0,
                        style={"background": PANEL2, "color": TXT,
                               "border": f"1px solid {BORDA}", "borderRadius": "8px",
                               "padding": "7px 14px", "cursor": "pointer",
                               "fontSize": "11px", "letterSpacing": "1px",
                               "fontFamily": FONTE}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "margin": "6px 0 8px"}),

        html.Div(id="grade"),

        html.Div(style={"marginTop": "16px", "background": PANEL,
                        "borderRadius": "14px", "border": f"1px solid {BORDA}",
                        "padding": "8px"},
                 children=[dcc.Graph(id="detalhe",
                                     config={"displayModeBar": False})]),

        html.Div("Fontes: BCB/SGS e IBGE/SIDRA. Leitura qualitativa, "
                 "não é datação oficial de recessão.",
                 style={"fontSize": "10px", "color": TXT_DIM,
                        "marginTop": "12px"}),
    ])


app.layout = _layout


# ---- relógio ao vivo (sem ida ao servidor) -----------------------------------
app.clientside_callback(
    "function(n){const d=new Date();const p=x=>String(x).padStart(2,'0');"
    "return [p(d.getDate())+'-'+p(d.getMonth()+1)+'-'+d.getFullYear(),"
    "p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds())];}",
    Output("relogio-data", "children"),
    Output("relogio-hora", "children"),
    Input("tick", "n_intervals"))


# ---- monta cockpit + grade a partir do payload (load e refresh) --------------
@app.callback(Output("cockpit", "children"), Output("grade", "children"),
              Input("payload", "data"))
def _construir(p):
    return _cockpit(p), _grade(p)


# ---- botão atualizar: recoleta dados ao vivo ---------------------------------
@app.callback(Output("payload", "data"), Input("btn-refresh", "n_clicks"),
              prevent_initial_call=True)
def _refresh(n):
    return painel_dados.montar_payload(usar_cache=False)


# ---- drill-down: clique no instrumento abre a série no radar -----------------
@app.callback(Output("detalhe", "figure"),
              Input({"type": "instr", "index": ALL}, "n_clicks"),
              State("payload", "data"))
def _detalhe(_clicks, p):
    indby = {i["chave"]: i for i in p["indicadores"]}
    alvo = None
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict):
        alvo = ctx.triggered_id.get("index")
    if alvo not in indby:
        # padrão: primeiro indicador de núcleo (IBC-Br)
        alvo = next((i["chave"] for i in p["indicadores"] if i["nucleo"]),
                    p["indicadores"][0]["chave"])
    return _figura_serie(indby[alvo])


def main():
    print("Dashboard em http://127.0.0.1:8050  (Ctrl+C para encerrar)")
    app.run(debug=False, port=8050)


if __name__ == "__main__":
    main()
