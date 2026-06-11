# -*- coding: utf-8 -*-
"""
Dashboard visual do Painel do Ciclo Econômico (estilo "painel de avião").

Leitura imediata: no topo, o ESTÁGIO da economia em cor + medidores.
Drill-down: clique em qualquer instrumento para ver a série histórica.

Rodar:
    python -m painel_ciclo.dashboard
    # abra http://127.0.0.1:8050 no navegador
"""
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, ALL, ctx

from . import painel_dados

# ---------------------------------------------------------------- paleta cockpit
BG = "#0e1726"          # fundo geral (azul-escuro de painel)
PANEL = "#16233b"       # cartões
PANEL2 = "#1d2f4e"      # cartões hover/realce
TXT = "#e8eef7"         # texto claro
TXT_DIM = "#8ba0bf"     # texto secundário
BORDA = "#26395c"

CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"


# ---------------------------------------------------------------- helpers de UI
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


def _sparkline(ind):
    s = ind["serie"]
    n = min(len(s["valores"]), 36)
    x = s["datas"][-n:]
    y = s["valores"][-n:]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines",
                               line=dict(color=ind["cor_hex"], width=2),
                               hoverinfo="skip"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=44,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      showlegend=False)
    return dcc.Graph(figure=fig, config={"displayModeBar": False, "staticPlot": True},
                     style={"height": "44px"})


def _instrumento(ind):
    nucleo_tag = (html.Span("núcleo", style={
        "fontSize": "9px", "color": "#0e1726", "background": "#5aa9e6",
        "borderRadius": "3px", "padding": "1px 5px", "marginLeft": "6px"})
        if ind["nucleo"] else None)
    return html.Button(
        id={"type": "instr", "index": ind["chave"]}, n_clicks=0,
        style={
            "background": PANEL, "border": f"1px solid {BORDA}",
            "borderRadius": "10px", "padding": "10px 12px", "width": "232px",
            "textAlign": "left", "cursor": "pointer", "color": TXT,
            "borderLeft": f"6px solid {ind['cor_hex']}", "margin": "0",
        },
        children=[
            html.Div([
                html.Span("●", style={"color": ind["cor_hex"], "fontSize": "15px",
                                      "marginRight": "6px"}),
                html.Span(ind["rotulo"], style={"fontSize": "12.5px",
                                               "fontWeight": "600"}),
                nucleo_tag,
            ], style={"display": "flex", "alignItems": "center",
                      "marginBottom": "4px", "minHeight": "34px"}),
            html.Div([
                html.Span(_fmt_num(ind["nivel"]),
                          style={"fontSize": "20px", "fontWeight": "700"}),
                html.Span(f"  ref. {ind['referencia']}",
                          style={"fontSize": "10px", "color": TXT_DIM}),
            ]),
            html.Div([
                html.Span(f"mês {_fmt_var(ind['var_mensal'], ind['unidade'])}",
                          style={"marginRight": "8px"}),
                html.Span(f"MM3M {_fmt_var(ind['var_mm3_3m'], ind['unidade'])}"),
            ], style={"fontSize": "10.5px", "color": TXT_DIM, "marginTop": "2px"}),
            _sparkline(ind),
            html.Div(f"sinal: {ind['sinal_txt']}",
                     style={"fontSize": "9.5px", "color": ind["cor_hex"],
                            "marginTop": "2px"}),
        ])


def _gauge_ct(diag):
    ct = diag.get("ct")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=(ct if ct is not None else 0),
        number={"font": {"size": 30, "color": TXT}, "suffix": " / 2"},
        gauge={
            "axis": {"range": [0, 2], "tickvals": [0, 1, 2],
                     "tickcolor": TXT_DIM, "tickfont": {"color": TXT_DIM}},
            "bar": {"color": "rgba(255,255,255,0.85)", "thickness": 0.18},
            "borderwidth": 0,
            "steps": [
                {"range": [0, 0.67], "color": "#2e9e4f"},
                {"range": [0.67, 1.33], "color": "#e8c12a"},
                {"range": [1.33, 2], "color": "#d8362a"},
            ],
        }))
    fig.update_layout(height=170, margin=dict(l=20, r=20, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": TXT})
    return fig


def _gauge_difusao(diag):
    val = (diag.get("share_pos") or 0) * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number={"font": {"size": 30, "color": TXT}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TXT_DIM,
                     "tickfont": {"color": TXT_DIM}},
            "bar": {"color": "rgba(255,255,255,0.85)", "thickness": 0.18},
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "#d8362a"},
                {"range": [40, 60], "color": "#e8c12a"},
                {"range": [60, 100], "color": "#2e9e4f"},
            ],
        }))
    fig.update_layout(height=170, margin=dict(l=20, r=20, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": TXT})
    return fig


def _figura_serie(ind):
    s = ind["serie"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["datas"], y=s["valores"], mode="lines",
                             name="Nível", line=dict(color=ind["cor_hex"], width=2.2)))
    fig.add_trace(go.Scatter(x=s["datas"], y=s["mm3"], mode="lines",
                             name="MM3M", line=dict(color="#ffffff", width=1.4, dash="dash")))
    fig.update_layout(
        height=430, margin=dict(l=50, r=20, t=50, b=40),
        title=dict(text=f"{ind['rotulo']} — série histórica (ref. {ind['referencia']})",
                   font={"color": TXT, "size": 16}),
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, font={"color": TXT_DIM},
        legend=dict(orientation="h", y=1.06, x=0, font={"color": TXT}),
        xaxis=dict(gridcolor=BORDA, rangeslider=dict(visible=True, thickness=0.06)),
        yaxis=dict(gridcolor=BORDA))
    return fig


def _cockpit(p):
    diag = p["diag"]
    ct = diag.get("ct")
    share = (diag.get("share_pos") or 0) * 100
    status = html.Div([
        html.Div("ESTÁGIO DO CICLO (bloco coincidente)",
                 style={"fontSize": "11px", "color": TXT_DIM, "letterSpacing": "1px"}),
        html.Div(p["estagio_rotulo"],
                 style={"fontSize": "34px", "fontWeight": "800", "color": "#fff",
                        "lineHeight": "1.1", "margin": "6px 0"}),
        html.Div(f"Ct = {ct}  •  difusão positiva {share:.0f}%  •  "
                 f"{diag.get('n_pos','?')} crescendo / {diag.get('n_neg','?')} caindo",
                 style={"fontSize": "13px", "color": "#f2f6fc"}),
        html.Div(f"Fechamento {p['fechamento']} · alvo {p['referencia_alvo']} · "
                 f"gerado em {p['gerado_em']}",
                 style={"fontSize": "11px", "color": "rgba(255,255,255,0.8)",
                        "marginTop": "8px"}),
    ], style={"flex": "1.4", "background": p["estagio_hex"], "borderRadius": "12px",
              "padding": "18px 22px", "minWidth": "320px"})

    g1 = html.Div([
        html.Div("PONTUAÇÃO COINCIDENTE (Ct)",
                 style={"fontSize": "11px", "color": TXT_DIM, "textAlign": "center"}),
        dcc.Graph(figure=_gauge_ct(diag), config={"displayModeBar": False}),
        html.Div("0 favorável · 1 misto · 2 deterioração",
                 style={"fontSize": "10px", "color": TXT_DIM, "textAlign": "center"}),
    ], style={"flex": "1", "background": PANEL, "borderRadius": "12px",
              "padding": "12px", "border": f"1px solid {BORDA}"})

    g2 = html.Div([
        html.Div("DIFUSÃO POSITIVA DO NÚCLEO",
                 style={"fontSize": "11px", "color": TXT_DIM, "textAlign": "center"}),
        dcc.Graph(figure=_gauge_difusao(diag), config={"displayModeBar": False}),
        html.Div("% de indicadores de núcleo crescendo",
                 style={"fontSize": "10px", "color": TXT_DIM, "textAlign": "center"}),
    ], style={"flex": "1", "background": PANEL, "borderRadius": "12px",
              "padding": "12px", "border": f"1px solid {BORDA}"})

    return html.Div([status, g1, g2],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap",
                           "marginBottom": "16px"})


def _escala_legenda():
    itens = [("EXPANSÃO", "#2e9e4f"), ("DESACELERAÇÃO", "#e8c12a"),
             ("ALERTA", "#e8821a"), ("RECESSÃO", "#d8362a"), ("CONTRAÇÃO", "#7a3ea8")]
    chips = [html.Span(nome, style={
        "background": cor, "color": "#0e1726" if cor != "#7a3ea8" else "#fff",
        "padding": "3px 10px", "borderRadius": "20px", "fontSize": "11px",
        "fontWeight": "700", "marginRight": "8px"}) for nome, cor in itens]
    return html.Div([
        html.Span("Escala de alerta (Et 0–8): ",
                  style={"color": TXT_DIM, "fontSize": "11px", "marginRight": "8px"}),
        *chips,
        html.Span("  — hoje só o bloco coincidente (1 de 4) está implementado.",
                  style={"color": TXT_DIM, "fontSize": "11px"}),
    ], style={"margin": "4px 0 18px"})


def _grade(p):
    secoes = []
    for dim in p["dimensoes"]:
        cards = [_instrumento(i) for i in p["indicadores"] if i["dimensao"] == dim]
        secoes.append(html.Div([
            html.Div(dim.upper(), style={
                "fontSize": "12px", "color": TXT_DIM, "fontWeight": "700",
                "letterSpacing": "1px", "margin": "14px 0 8px"}),
            html.Div(cards, style={"display": "flex", "flexWrap": "wrap", "gap": "10px"}),
        ]))
    return html.Div(secoes)


# ---------------------------------------------------------------- app
app = Dash(__name__, external_scripts=[CDN_PLOTLY],
           title="Painel do Ciclo Econômico")
server = app.server

_PAYLOAD_INICIAL = painel_dados.montar_payload(usar_cache=True)


def _layout():
    return html.Div(style={"background": BG, "minHeight": "100vh",
                           "padding": "20px 26px", "fontFamily": "Segoe UI, Arial, sans-serif"},
                    children=[
        dcc.Store(id="payload", data=_PAYLOAD_INICIAL),
        html.Div([
            html.Div([
                html.Span("✈ ", style={"fontSize": "22px"}),
                html.Span("Painel de Monitoramento do Ciclo Econômico",
                          style={"fontSize": "22px", "fontWeight": "800", "color": TXT}),
            ]),
            html.Button("⟳ Atualizar dados (ao vivo)", id="btn-refresh", n_clicks=0,
                        style={"background": PANEL2, "color": TXT, "border": f"1px solid {BORDA}",
                               "borderRadius": "8px", "padding": "8px 14px", "cursor": "pointer"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "marginBottom": "12px"}),
        _escala_legenda(),
        html.Div(id="cockpit"),
        html.Div("INSTRUMENTOS  ·  clique em um indicador para ver a série",
                 style={"fontSize": "12px", "color": TXT_DIM, "fontWeight": "700",
                        "letterSpacing": "1px", "margin": "6px 0 2px"}),
        html.Div(id="grade"),
        html.Div(style={"marginTop": "18px", "background": PANEL, "borderRadius": "12px",
                        "border": f"1px solid {BORDA}", "padding": "8px"},
                 children=[dcc.Graph(id="detalhe", config={"displayModeBar": False})]),
        html.Div("Fontes: BCB/SGS e IBGE/SIDRA. Leitura qualitativa, não é datação oficial de recessão.",
                 style={"fontSize": "10.5px", "color": TXT_DIM, "marginTop": "12px"}),
    ])


app.layout = _layout


# ---- monta cockpit + grade a partir do payload (load e refresh) -------------
@app.callback(Output("cockpit", "children"), Output("grade", "children"),
              Input("payload", "data"))
def _construir(p):
    return _cockpit(p), _grade(p)


# ---- botão atualizar: recoleta dados ao vivo --------------------------------
@app.callback(Output("payload", "data"), Input("btn-refresh", "n_clicks"),
              prevent_initial_call=True)
def _refresh(n):
    return painel_dados.montar_payload(usar_cache=False)


# ---- drill-down: clique no instrumento mostra a série -----------------------
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
