# -*- coding: utf-8 -*-
"""
Exporta o painel como SITE ESTÁTICO (HTML+JS único) para o GitHub Pages.

Gera `painel_ciclo/site/index.html` com:
  - os dados de todos os indicadores embutidos em JSON;
  - a mesma navegação do dashboard (home -> setor -> detalhe), feita em
    JavaScript puro com roteamento por hash (#s/industria, #i/pim_geral);
  - gráficos Plotly via CDN, termômetro e sparklines em SVG.

Sem servidor: a "atualização" passa a ser o GitHub Action agendado que
roda este módulo e republica a página.

Rodar:
    python -m painel_ciclo.exporta_site
    # coleta dados das fontes (com fallback no cache local) e gera o site
"""
import io
import json
import os
import sys

from . import config
from . import painel_dados
from .textos import TEXTOS

DIR_SITE = os.path.join(os.path.dirname(__file__), "site")
TEMPLATE_ATUAL = os.path.join(os.path.dirname(__file__), "site_template.html")


# o template usa __TOKENS__ em vez de f-string para não conflitar com as
# chaves {} do JavaScript/CSS
TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Indicadores — Panorama Macroeconômico</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{
  --bg:#eef0f5; --branco:#ffffff; --navy:#1c2e6b; --cinza:#6b7280;
  --verde:#179a55; --amarelo:#f2b600; --laranja:#f08c00;
  --vermelho:#e23a2e; --roxo:#6a3fa0;
  --sombra:0 4px 14px rgba(28,46,107,0.10);
  --f-titulo:'Playfair Display',Georgia,serif;
  --f-corpo:'Inter','Segoe UI',Arial,sans-serif;
}
*{box-sizing:border-box}
body{background:var(--bg);margin:0;padding:26px 34px;font-family:var(--f-corpo);color:#111}
button{font-family:var(--f-corpo)}
.cabecalho{display:flex;justify-content:space-between;align-items:flex-start}
.titulo{font-family:var(--f-titulo);font-size:42px;font-weight:700;color:var(--navy);line-height:1.05}
.subtitulo{font-size:13px;color:#8b93a5;letter-spacing:2.5px;margin-top:4px}
.risco{width:110px;height:3px;background:var(--navy);margin-top:10px;border-radius:2px}
.selo-atualizacao{background:var(--branco);color:var(--navy);font-weight:600;font-size:12px;
  border:1px solid #dde1ea;border-radius:10px;padding:10px 16px;box-shadow:var(--sombra)}
.abas{display:flex;gap:12px;margin:18px 0 22px}
.aba{display:flex;align-items:center;gap:8px;border-radius:24px;padding:10px 22px;
  font-size:13px;font-weight:700;letter-spacing:.5px}
.aba.ativa{background:var(--navy);color:#fff;border:none;box-shadow:var(--sombra)}
.aba.inativa{background:var(--branco);color:#9aa3b2;border:1px solid #dde1ea;cursor:not-allowed}
.linha-home{display:flex;gap:18px;align-items:stretch}
.grade{display:grid;grid-template-columns:repeat(3,minmax(260px,1fr));gap:18px;flex:1;min-width:0}
@media (max-width:1100px){.linha-home{flex-wrap:wrap}.grade{grid-template-columns:repeat(2,minmax(260px,1fr))}}
@media (max-width:700px){.grade{grid-template-columns:1fr}}
.cartao{color:#fff;border:none;border-radius:16px;padding:20px 22px;width:100%;
  min-height:280px;display:flex;flex-direction:column;align-items:stretch;
  text-align:left;cursor:pointer;box-shadow:var(--sombra)}
.cartao .topo{display:flex;align-items:flex-start;gap:10px}
.cartao .nome{font-size:24px;font-weight:700;line-height:1.15;flex:1;min-width:0}
.cartao .sub{font-size:12px;opacity:.85;margin-top:3px}
.cartao .valor{font-size:38px;font-weight:700;margin:12px 0 2px}
.cartao .ref{font-size:15px;font-weight:600}
.cartao .legenda{font-size:12px;opacity:.9;margin-top:3px}
.cartao img.spark{width:100%;height:30px;margin-top:auto;padding-top:10px}
.termometro{background:var(--branco);border-radius:16px;box-shadow:var(--sombra);
  padding:22px 24px;width:300px;flex-shrink:0;text-align:center;display:flex;
  flex-direction:column;justify-content:center}
.barra-setor{border-radius:14px;padding:14px 20px;display:flex;align-items:center;
  margin-bottom:18px;box-shadow:var(--sombra);color:#fff}
.barra-setor .voltar{background:transparent;border:none;color:#fff;font-size:16px;
  font-weight:700;cursor:pointer;padding:0}
.barra-setor .nome{font-size:22px;font-weight:700;margin-left:6px}
.pills{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.pill{border:1px solid #e2e6ee;border-radius:20px;padding:7px 14px;font-size:12px;
  font-weight:600;cursor:pointer;box-shadow:var(--sombra)}
.meta{display:flex;align-items:flex-start;gap:16px;margin:2px 4px 12px}
.meta .rotulo{font-size:28px;font-weight:700}
.meta .sinal{font-size:13px;color:var(--cinza);margin-top:4px}
.meta .direita{text-align:right;font-size:11px;color:var(--cinza);letter-spacing:.5px;margin-left:auto}
.faixa-metricas{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}
.caixa-metrica{background:var(--branco);border-radius:14px;padding:14px 18px;flex:1;
  min-width:220px;box-shadow:var(--sombra)}
.caixa-metrica .num{font-size:11px;font-weight:700;color:var(--cinza);letter-spacing:1px}
.caixa-metrica .titulo-m{font-size:14px;font-weight:700;color:var(--navy);margin-top:2px}
.caixa-metrica .valor-m{font-size:28px;font-weight:700;margin:6px 0 2px}
.caixa-metrica .desc{font-size:12px;color:var(--cinza);line-height:1.4}
.linha-graficos{display:flex;gap:14px;flex-wrap:wrap}
.painel-grafico{background:var(--branco);border-radius:14px;padding:10px;flex:2.2;
  min-width:420px;box-shadow:var(--sombra)}
.painel-12m{background:var(--branco);border-radius:14px;flex:1;min-width:260px;box-shadow:var(--sombra)}
.painel-12m .titulo-12m{font-weight:700;color:var(--navy);font-size:15px;margin:8px 8px 0;padding:8px 8px 0}
.painel-12m .stats{display:flex;justify-content:space-around;padding:4px 8px 12px}
.painel-12m .stats .nome-s{font-size:11px;color:var(--cinza)}
.painel-12m .stats .val-s{font-size:20px;font-weight:700}
.fichas-titulo{font-weight:700;letter-spacing:1px;font-size:13px;margin:20px 4px 10px}
.fichas{display:flex;gap:14px;flex-wrap:wrap}
.ficha{background:var(--branco);border-radius:14px;padding:18px;flex:1;min-width:240px;box-shadow:var(--sombra)}
.ficha .cab{margin-bottom:8px}
.ficha .cab .ic{font-size:17px}
.ficha .cab .ti{font-weight:700;font-size:15px}
.ficha .tx{font-size:13px;color:#4b5563;line-height:1.6}
.rodape{font-size:12px;margin-top:26px;color:var(--cinza)}
.rodape b{color:var(--navy)}
</style>
</head>
<body>
<div class="cabecalho">
  <div>
    <div class="titulo">INDICADORES</div>
    <div class="subtitulo">PANORAMA MACROECONÔMICO — CICLO DE NEGÓCIOS</div>
    <div class="risco"></div>
  </div>
  <div class="selo-atualizacao">⟳ Atualização automática · <span id="gerado-em"></span></div>
</div>
<div class="abas">
  <div class="aba inativa" title="Tópico 2 — em construção">🕐 ANTECEDENTES</div>
  <div class="aba ativa">📊 COINCIDENTES</div>
  <div class="aba inativa" title="Tópico 3 — em construção">⏳ DEFASADOS</div>
</div>
<div id="conteudo"></div>
<div class="rodape" id="rodape"></div>

<script>
const P = __PAYLOAD__;
const TEXTOS = __TEXTOS__;
const SETORES = __SETORES__;

const NAVY="#1c2e6b", CINZA="#6b7280", VERDE="#179a55", AMARELO="#f2b600",
      LARANJA="#f08c00", VERMELHO="#e23a2e", ROXO="#6a3fa0",
      F_CORPO="'Inter','Segoe UI',Arial,sans-serif";
const DEADBAND = 0.05;

// ----------------------------------------------------------- formatação
function fmtNum(v, dec=1){
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", {minimumFractionDigits: dec, maximumFractionDigits: dec});
}
function fmtVar(v, unidade="%"){
  if (v === null || v === undefined) return "—";
  const sinal = v >= 0 ? "+" : "−";
  const a = Math.abs(v);
  if (unidade === "%")    return sinal + a.toLocaleString("pt-BR",{minimumFractionDigits:1,maximumFractionDigits:1}) + "%";
  if (unidade === "p.p.") return sinal + a.toLocaleString("pt-BR",{minimumFractionDigits:1,maximumFractionDigits:1}) + " p.p.";
  return sinal + a.toLocaleString("pt-BR",{maximumFractionDigits:0});
}
function mesPt(ref){
  if (!ref || !ref.includes("-")) return ref || "—";
  const [ano, mes] = ref.split("-");
  const nomes = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
  return nomes[parseInt(mes,10)-1] + ". " + ano;
}
function esc(t){ const d=document.createElement("div"); d.textContent=t??""; return d.innerHTML; }

// ----------------------------------------------------------- status/seta
function momentum(ind){
  const v = ind.var_mm3_3m;
  if (v === null || v === undefined) return 0;
  const mm3 = (ind.serie?.mm3 || []).filter(x => x !== null && x !== undefined);
  const ult = mm3.slice(-25);
  const difs = [];
  for (let i = 1; i < ult.length; i++) difs.push(ult[i] - ult[i-1]);
  if (difs.length >= 6){
    const media = difs.reduce((a,b)=>a+b,0)/difs.length;
    const dp = Math.sqrt(difs.reduce((a,d)=>a+(d-media)**2,0)/difs.length);
    if (dp > 1e-12) return Math.max(-2, Math.min(2, v/(3*dp)));
  }
  return v > 0 ? 1 : (v < 0 ? -1 : 0);
}
function statusDe(cor, z){
  if (cor === "verde")
    return z >= 0.9 ? {hex:VERDE, ang:-90, rotulo:"melhora forte"}
                    : {hex:VERDE, ang:-45, rotulo:"melhorando"};
  if (cor === "vermelho")
    return z <= -0.9 ? {hex:VERMELHO, ang:90, rotulo:"piora forte"}
                     : {hex:LARANJA, ang:45, rotulo:"piorando"};
  return {hex:AMARELO, ang:0, rotulo:"estável"};
}
function statusInd(ind){
  const z = momentum(ind);
  if ((ind.tipo || "indice") === "indice"){
    const v3 = ind.var_mm3_3m;
    let cor = "amarelo";
    if (v3 !== null && v3 !== undefined){
      if (v3 > DEADBAND) cor = "verde";
      else if (v3 < -DEADBAND) cor = "vermelho";
    }
    return statusDe(cor, z);
  }
  return statusDe(ind.cor, z);
}
function statusSetor(grupo){
  const comSinal = grupo.filter(i => i.sinal_txt !== "sem dados");
  if (!comSinal.length) return statusDe("amarelo", 0);
  const stats = comSinal.map(statusInd);
  const pos = stats.filter(s => s.hex === VERDE).length;
  const neg = stats.filter(s => s.hex === LARANJA || s.hex === VERMELHO).length;
  const share = pos / stats.length;
  const zMed = comSinal.reduce((a,i)=>a+momentum(i),0)/comSinal.length;
  if (share >= 0.6) return statusDe("verde", zMed);
  if (share >= 0.4 && neg < stats.length/2) return statusDe("amarelo", zMed);
  return statusDe("vermelho", zMed);
}
function contaAltas(grupo){ return grupo.filter(i => statusInd(i).hex === VERDE).length; }
function grupoDe(setor){ return P.indicadores.filter(i => setor.dims.includes(i.dimensao)); }
function setorPorSlug(slug){ return SETORES.find(s => s.slug === slug); }

// ----------------------------------------------------------- SVG helpers
function svgUri(corpo, w, h){
  return "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${corpo}</svg>`);
}
function setaIcone(ang, tam=64){
  const corpo = `<circle cx="32" cy="32" r="27" stroke="white" stroke-width="2.6" fill="none"/>`
    + `<g transform="rotate(${ang} 32 32)">`
    + `<path d="M21 32 H42 M34 23 L43 32 L34 41" stroke="white" stroke-width="4" `
    + `fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>`;
  return `<img src="${svgUri(corpo,64,64)}" style="width:${tam}px;height:${tam}px;flex-shrink:0" alt="">`;
}
function sparkBranca(serie, w=250, h=30){
  const vals = (serie?.valores || []).filter(v => v !== null && v !== undefined).slice(-36);
  if (vals.length < 2) return `<div style="height:${h}px"></div>`;
  const vmin = Math.min(...vals), vmax = Math.max(...vals);
  const amp = (vmax - vmin) || 1, pad = 2;
  const pts = vals.map((v,i) => {
    const x = pad + i*(w-2*pad)/(vals.length-1);
    const y = h - pad - (v - vmin)/amp*(h-2*pad);
    return x.toFixed(1) + "," + y.toFixed(1);
  }).join(" ");
  const corpo = `<polyline points="${pts}" fill="none" stroke="white" stroke-width="1.6" opacity="0.9" stroke-linejoin="round"/>`;
  return `<img class="spark" src="${svgUri(corpo,w,h)}" alt="">`;
}

// ----------------------------------------------------------- termômetro
function termometro(){
  const val = (P.diag.share_pos || 0) * 100;
  const cx=130, cy=132, R=96;
  const segs = [[0,22,ROXO],[22,44,VERMELHO],[44,67,LARANJA],[67,78,AMARELO],[78,100,VERDE]];
  const ponto = (v, raio) => {
    const th = (180 - v*1.8) * Math.PI/180;
    return [cx + raio*Math.cos(th), cy - raio*Math.sin(th)];
  };
  let corpo = "";
  for (const [a,b,cor] of segs){
    const [x0,y0] = ponto(a+1, R), [x1,y1] = ponto(b-1, R);
    corpo += `<path d="M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${R} ${R} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}" stroke="${cor}" stroke-width="26" fill="none"/>`;
  }
  for (const v of [0,20,40,60,80,100]){
    const [x,y] = ponto(v, R+24);
    corpo += `<text x="${x.toFixed(0)}" y="${y.toFixed(0)}" text-anchor="middle" fill="${CINZA}" font-family="Arial" font-size="12">${v}</text>`;
  }
  const [xp,yp] = ponto(Math.max(2, Math.min(98, val)), R-24);
  corpo += `<line x1="${cx}" y1="${cy}" x2="${xp.toFixed(1)}" y2="${yp.toFixed(1)}" stroke="${NAVY}" stroke-width="5" stroke-linecap="round"/>`
        + `<circle cx="${cx}" cy="${cy}" r="7" fill="white" stroke="${NAVY}" stroke-width="4"/>`;
  const hx = P.estagio_hex || VERDE;
  return `<div class="termometro">
    <div style="color:${NAVY};font-weight:700;font-size:16px;letter-spacing:.5px">TERMÔMETRO DO</div>
    <div style="color:${NAVY};font-weight:700;font-size:16px;letter-spacing:.5px;margin-bottom:8px">CICLO ECONÔMICO</div>
    <img src="${svgUri(corpo,260,160)}" style="width:260px;height:160px;align-self:center" alt="">
    <div style="font-size:40px;font-weight:700;color:${hx};line-height:1.1">${fmtNum(val,0)}%</div>
    <div style="margin:8px 0 6px"><span style="background:${hx};color:#fff;border-radius:16px;padding:4px 14px;font-size:12px;font-weight:700;letter-spacing:.5px">${esc(P.estagio_rotulo||"—")}</span></div>
    <div style="font-size:12px;color:${NAVY};font-weight:600">Difusão positiva do núcleo · ref. ${mesPt(P.referencia_alvo)}</div>
    <div style="font-size:11px;color:${CINZA};margin-top:2px">% dos indicadores centrais em expansão</div>
  </div>`;
}

// ----------------------------------------------------------- cartões
function valorDestaque(ind){
  const t = ind.tipo || "indice";
  if (t === "taxa")
    return [fmtNum(ind.nivel,1) + "%", "Taxa no trimestre móvel (subir é piora)"];
  if (t === "fluxo"){
    const v = ind.nivel;
    const corpo = (v===null||v===undefined) ? "—"
      : (v >= 0 ? "+" : "−") + Math.abs(v).toLocaleString("pt-BR",{maximumFractionDigits:0});
    return [corpo, "Saldo do mês: admissões − desligamentos"];
  }
  const sufixo = /^(ibcbr|pib|pim|pmc|pms)/.test(ind.chave) ? " (dessaz.)" : "";
  return [fmtVar(ind.var_mm3_3m,"%"),
          `Tendência de 3 meses${sufixo} · mês: ${fmtVar(ind.var_mensal,"%")}`];
}
function cartao(titulo, valor, ref, legenda, status, onclick, spark, subtitulo){
  return `<button class="cartao" style="background:${status.hex}" onclick="${onclick}">
    <div class="topo">
      <div style="flex:1;min-width:0">
        <div class="nome">${titulo}</div>
        ${subtitulo ? `<div class="sub">${esc(subtitulo)}</div>` : ""}
      </div>
      ${setaIcone(status.ang)}
    </div>
    <div class="valor">${esc(valor)}</div>
    <div class="ref">${mesPt(ref)}</div>
    <div class="legenda">${esc(legenda)}</div>
    ${spark || ""}
  </button>`;
}

// ----------------------------------------------------------- gráficos
function figSerieCompleta(div, ind, status){
  const s = ind.serie, datas = s.datas, vals = s.valores;
  const ult = vals.slice(-60).filter(v => v !== null && v !== undefined);
  const media = ult.length ? ult.reduce((a,b)=>a+b,0)/ult.length : 0;
  const dp = ult.length ? Math.sqrt(ult.reduce((a,v)=>a+(v-media)**2,0)/ult.length) : 0;
  const ann = [];
  if (vals.length && vals[vals.length-1] !== null)
    ann.push({x:datas[datas.length-1], y:vals[vals.length-1],
      text:"<b>"+fmtNum(vals[vals.length-1],1)+"</b>", showarrow:true, arrowhead:0,
      ax:42, ay:-26, font:{color:"#fff",size:13}, bgcolor:status.hex, borderpad:5});
  for (let i = s.mm3.length-1; i >= 0; i--){
    if (s.mm3[i] !== null && s.mm3[i] !== undefined){
      ann.push({x:datas[i], y:s.mm3[i], text:"<b>"+fmtNum(s.mm3[i],1)+"</b>",
        showarrow:true, arrowhead:0, ax:42, ay:22,
        font:{color:"#fff",size:13}, bgcolor:NAVY, borderpad:5});
      break;
    }
  }
  Plotly.newPlot(div, [
    {x:datas, y:vals, mode:"lines", name:"Série", line:{color:status.hex, width:2.4}},
    {x:datas, y:s.mm3, mode:"lines", name:"Média móvel 3m", line:{color:NAVY, width:1.4, dash:"dash"}},
  ], {
    height:420, margin:{l:46,r:24,t:28,b:36}, paper_bgcolor:"#fff", plot_bgcolor:"#fff",
    font:{family:F_CORPO, color:CINZA}, legend:{orientation:"h", y:1.08, x:0},
    xaxis:{gridcolor:"#eceff5", rangeslider:{visible:true, thickness:0.05}},
    yaxis:{gridcolor:"#eceff5"}, annotations:ann,
    shapes:[
      {type:"rect", xref:"paper", x0:0, x1:1, y0:media-dp, y1:media+dp,
       fillcolor:status.hex, opacity:0.10, line:{width:0}},
      {type:"line", xref:"paper", x0:0, x1:1, y0:media, y1:media,
       line:{color:status.hex, width:1, dash:"dot"}, opacity:0.6},
    ],
  }, {displayModeBar:false, responsive:true});
}
function fig12m(div, ind, status){
  const s = ind.serie;
  const datas = s.datas.slice(-12), vals = s.valores.slice(-12), mm3 = s.mm3.slice(-12);
  const ann = [];
  if (vals.length && vals[vals.length-1] !== null)
    ann.push({x:datas[datas.length-1], y:vals[vals.length-1],
      text:"<b>"+fmtNum(vals[vals.length-1],1)+"</b>", showarrow:true, arrowhead:0,
      ax:-34, ay:-20, font:{color:"#fff",size:11}, bgcolor:status.hex, borderpad:4});
  for (let i = mm3.length-1; i >= 0; i--){
    if (mm3[i] !== null && mm3[i] !== undefined){
      ann.push({x:datas[i], y:mm3[i], text:"<b>"+fmtNum(mm3[i],1)+"</b>",
        showarrow:true, arrowhead:0, ax:-34, ay:20,
        font:{color:"#fff",size:11}, bgcolor:NAVY, borderpad:4});
      break;
    }
  }
  Plotly.newPlot(div, [
    {x:datas, y:vals, mode:"lines+markers", name:"Série",
     line:{color:status.hex, width:2.4}, marker:{size:5}},
    {x:datas, y:mm3, mode:"lines", name:"Média móvel 3m",
     line:{color:NAVY, width:1.4, dash:"dash"}},
  ], {
    height:240, margin:{l:40,r:14,t:10,b:30}, paper_bgcolor:"#fff", plot_bgcolor:"#fff",
    font:{family:F_CORPO, color:CINZA, size:11}, xaxis:{gridcolor:"#eceff5"},
    yaxis:{gridcolor:"#eceff5"}, showlegend:false, annotations:ann,
  }, {displayModeBar:false, responsive:true});
}

// ----------------------------------------------------------- telas
function telaHome(){
  const cards = SETORES.map(s => {
    const grupo = grupoDe(s);
    if (!grupo.length) return "";
    const status = statusSetor(grupo);
    const destaque = grupo.find(i => i.nucleo) || grupo[0];
    const [valor] = valorDestaque(destaque);
    const legenda = `${destaque.rotulo} · ${contaAltas(grupo)} de ${grupo.length} indicadores em alta`;
    return cartao(`${s.icone} ${esc(s.nome)}`, valor, destaque.referencia, legenda,
                  status, `nav('s/${s.slug}')`, sparkBranca(destaque.serie));
  }).join("");
  return `<div class="linha-home"><div class="grade">${cards}</div>${termometro()}</div>`;
}

function telaSetor(slug){
  const setor = setorPorSlug(slug) || SETORES[0];
  const grupo = grupoDe(setor);
  const status = statusSetor(grupo);
  const cards = grupo.map(i => {
    const st = statusInd(i);
    const [valor, legenda] = valorDestaque(i);
    return cartao(esc(i.rotulo), valor, i.referencia, legenda, st,
                  `nav('i/${i.chave}/${setor.slug}')`, sparkBranca(i.serie), st.rotulo);
  }).join("");
  return `<div class="barra-setor" style="background:${status.hex}">
      <button class="voltar" onclick="nav('home')">←</button>
      <span class="nome">${setor.icone}  Termômetro — ${esc(setor.nome)}</span>
    </div>
    <div class="grade" style="display:grid">${cards}</div>`;
}

function caixaMetrica(numero, titulo, valor, descricao, corValor){
  return `<div class="caixa-metrica">
    <div class="num">MÉTRICA ${numero}</div>
    <div class="titulo-m">${titulo}</div>
    <div class="valor-m" style="color:${corValor}">${esc(valor)}</div>
    <div class="desc">${esc(descricao)}</div>
  </div>`;
}
function faixaMetricas(ind, status){
  const t = ind.tipo || "indice", u = ind.unidade || "%";
  let d1, d3;
  if (t === "taxa"){
    d1 = "Diferença da taxa sobre o período anterior, em pontos percentuais.";
    d3 = "Diferença da MM3M atual contra a dos 3 meses anteriores (p.p.).";
  } else if (t === "fluxo"){
    d1 = "Variação do nível sobre o mês anterior (o saldo pode cruzar zero).";
    d3 = "Diferença da MM3M atual contra a dos 3 meses anteriores (nível).";
  } else {
    d1 = "Variação percentual dessazonalizada sobre o mês anterior.";
    d3 = "Variação % da MM3M atual contra a dos 3 meses anteriores.";
  }
  return `<div class="faixa-metricas">
    ${caixaMetrica(1, "Variação no mês", fmtVar(ind.var_mensal, u), d1, NAVY)}
    ${caixaMetrica(2, "Média móvel de 3 meses", fmtNum(ind.mm3, 1),
        "Média do nível dos últimos 3 meses — suaviza oscilações pontuais da série.", NAVY)}
    ${caixaMetrica(3, "Tendência (MM3M vs. 3 meses)", fmtVar(ind.var_mm3_3m, u),
        d3 + " É a métrica que define a cor do indicador.", status.hex)}
  </div>`;
}

function telaDetalhe(chave, slug){
  const ind = P.indicadores.find(i => i.chave === chave) || P.indicadores[0];
  let setor = setorPorSlug(slug);
  if (!setor) setor = SETORES.find(s => s.dims.includes(ind.dimensao)) || SETORES[0];
  const status = statusInd(ind);
  const irmaos = grupoDe(setor);
  const s = ind.serie;

  const pills = irmaos.map(i => {
    const st = statusInd(i), atual = i.chave === ind.chave;
    return `<button class="pill" style="background:${atual ? st.hex : "#fff"};color:${atual ? "#fff" : "#374151"}"
      onclick="nav('i/${i.chave}/${setor.slug}')"><span style="color:${atual ? "#fff" : st.hex}">● </span>${esc(i.rotulo)}</button>`;
  }).join("");

  const ficha = (ic, ti, tx) => `<div class="ficha">
      <div class="cab"><span class="ic">${ic}  </span><span class="ti" style="color:${status.hex}">${ti}</span></div>
      <div class="tx">${esc(tx)}</div></div>`;
  const txt = TEXTOS[ind.chave] || {};

  return `<div class="barra-setor" style="background:${status.hex}">
      <button class="voltar" onclick="nav('s/${setor.slug}')">←</button>
      <span class="nome">Termômetro — ${esc(setor.nome)}</span>
    </div>
    <div class="pills">${pills}</div>
    <div class="meta">
      <div style="flex:1">
        <div class="rotulo" style="color:${status.hex}">${esc(ind.rotulo)}</div>
        <div class="sinal">sinal atual: ${status.rotulo} · mês ${fmtVar(ind.var_mensal, ind.unidade)} · MM3M ${fmtVar(ind.var_mm3_3m, ind.unidade)}</div>
      </div>
      <div class="direita">
        <div>${s.datas.length ? "VALORES DE " + mesPt(s.datas[0]).toUpperCase() + " A " + mesPt(s.datas[s.datas.length-1]).toUpperCase() : "—"}</div>
        <div style="margin-top:4px">FONTE: ${esc(ind.fonte_desc)}</div>
        <div style="margin-top:4px">Atualizado em ${esc(P.gerado_em)}</div>
      </div>
    </div>
    ${faixaMetricas(ind, status)}
    <div class="linha-graficos">
      <div class="painel-grafico"><div id="grafico-serie"></div></div>
      <div class="painel-12m">
        <div class="titulo-12m">Últimos 12 meses</div>
        <div id="grafico-12m"></div>
        <div class="stats">
          <div><div class="nome-s">Nível atual</div><div class="val-s" style="color:${status.hex}">${fmtNum(ind.nivel,1)}</div></div>
          <div><div class="nome-s">MM3M</div><div class="val-s" style="color:${NAVY}">${fmtNum(ind.mm3,1)}</div></div>
        </div>
      </div>
    </div>
    <div class="fichas-titulo" style="color:${status.hex}">SAIBA MAIS SOBRE O INDICADOR</div>
    <div class="fichas">
      ${ficha("ⓘ", "O que é?", txt.o_que || "—")}
      ${ficha("🎯", "Por que é importante?", txt.por_que || "—")}
      ${ficha("🔎", "Como interpretar?", txt.como || "—")}
    </div>`;
}

// ----------------------------------------------------------- roteamento
function nav(rota){ location.hash = rota; }
function render(){
  const rota = (location.hash || "#home").slice(1);
  const conteudo = document.getElementById("conteudo");
  const partes = rota.split("/");
  if (partes[0] === "s" && partes[1]){
    conteudo.innerHTML = telaSetor(partes[1]);
  } else if (partes[0] === "i" && partes[1]){
    conteudo.innerHTML = telaDetalhe(partes[1], partes[2]);
    const ind = P.indicadores.find(i => i.chave === partes[1]) || P.indicadores[0];
    const status = statusInd(ind);
    figSerieCompleta(document.getElementById("grafico-serie"), ind, status);
    fig12m(document.getElementById("grafico-12m"), ind, status);
  } else {
    conteudo.innerHTML = telaHome();
  }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", render);

document.getElementById("gerado-em").textContent = P.gerado_em;
document.getElementById("rodape").innerHTML =
  `<b>ⓘ</b> Variações em relação ao período anterior. <b>Fonte:</b> Banco Central (SGS) e IBGE (SIDRA). `
  + `<b>Atualizado em:</b> ${esc(P.gerado_em)}. Leitura qualitativa — não é datação oficial.`;
render();
</script>
</body>
</html>
"""


def gerar(usar_cache=True, destino=None):
    """Coleta os dados, monta o payload e grava site/index.html."""
    payload = painel_dados.montar_payload(usar_cache=usar_cache)
    with io.open(TEMPLATE_ATUAL, "r", encoding="utf-8") as f:
        template = f.read()
    pagina = (template
              .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
              .replace("__TEXTOS__", json.dumps(TEXTOS, ensure_ascii=False))
              .replace("__SETORES__", json.dumps(config.SETORES, ensure_ascii=False)))
    destino = destino or DIR_SITE
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, "index.html")
    with io.open(caminho, "w", encoding="utf-8") as f:
        f.write(pagina)
    # evita 404 ruidoso do GitHub Pages no console do navegador
    with io.open(os.path.join(destino, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    print(f"Site gerado em {caminho}")
    print(f"  estagio: {payload['estagio_rotulo']} · "
          f"difusao {100 * (payload['diag'].get('share_pos') or 0):.0f}% · "
          f"referencia {payload['referencia_alvo']}")
    return caminho


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    gerar(usar_cache=True)
