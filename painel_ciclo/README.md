# Painel de Monitoramento do Ciclo Econômico — Estrutura Coincidente

Implementação do **Tópico 1 (estrutura coincidente)** das *Orientações*
(`Orientacoes.pdf`). Coleta dados reais das fontes oficiais, calcula as três
métricas pedidas e classifica a cor do bloco coincidente (`Ct`, 0–2) do escore.

> Este é o **primeiro dos quatro blocos** do painel. As estruturas antecedente
> (Tópico 2), defasada (Tópico 3) e de difusão (Tópico 4) entram depois, no mesmo
> arcabouço, e somam-se em `Et = Ct + At + Dt + Ft` (0–8).

## Como rodar

### Dashboard visual (recomendado)

Visual "Indicadores / Panorama Macroeconômico" (esboços em `novo visual/`),
com navegação em **3 níveis**:

1. **Home** — cartões coloridos por **setor** (Atividade, Indústria, Comércio,
   Serviços, Trabalho e Renda, Emprego Formal) + **Termômetro do Ciclo**
   (difusão positiva 0–100 com ponteiro e estágio: EXPANSÃO → CONTRAÇÃO).
2. **Setor** — cartões dos indicadores daquele setor.
3. **Detalhe** — série completa com intervalo típico, últimos 12 meses e as
   fichas "O que é? / Por que é importante? / Como interpretar?" ([textos.py](textos.py)).

Leitura leiga: a **cor do cartão** e a **seta** contam a história
(verde ↑/↗ melhorando · amarelo → estável · laranja ↘ piorando ·
vermelho ↓ piora forte). O número grande segue a *tendência de 3 meses* —
a mesma métrica que define a cor. Séries invertidas (desocupação) já
consideram que subir é piora.

```powershell
# a partir de C:\Users\suporte\Documents\gdo
python -m painel_ciclo.dashboard
# abra http://127.0.0.1:8050 no navegador
```

- Botão **"⟳ Atualizar dados"** recoleta tudo das fontes na hora.
- Abas ANTECEDENTES e DEFASADOS ficam desabilitadas até os Tópicos 2 e 3.
- Usa Plotly via CDN (precisa de internet para carregar os gráficos).

### Site estático / GitHub Pages

O painel também pode ser publicado como **página estática** (sem servidor
Python): mesmo visual e navegação, com os dados embutidos na página.

```powershell
python -m painel_ciclo.exporta_site
# gera painel_ciclo/site/index.html (abra direto no navegador)
```

Publicação online: o workflow [.github/workflows/publica.yml](../.github/workflows/publica.yml)
roda no GitHub Actions **todo dia às 09:00 (Brasília)** — e a cada push —,
recoleta os dados das fontes e republica o site no GitHub Pages. Passos
(uma única vez):

1. Crie um repositório no GitHub e suba esta pasta (`gdo/`).
2. No repositório: **Settings → Pages → Source: GitHub Actions**.
3. Pronto — o painel fica em `https://<usuario>.github.io/<repositorio>/`.

O cache em `painel_ciclo/dados/` é commitado de propósito: se alguma API
do BCB/IBGE estiver fora do ar durante o build, o site sai com o último
dado conhecido em vez de falhar.

### Relatório (linha de comando)

```powershell
python -m painel_ciclo.run            # busca dados reais nas fontes
python -m painel_ciclo.run --offline  # usa cache local se a fonte falhar
```

Saídas em `painel_ciclo/saidas/`:
- `coincidente_<fechamento>.csv` — métricas por indicador (abre no Excel);
- `coincidente_<fechamento>.md` — nota do bloco (cor, `Ct`, difusão, leitura).

Dados brutos ficam em cache em `painel_ciclo/dados/` (um CSV por série).

## As três métricas (conforme as Orientações)

Para cada indicador:
1. **Variação mensal dessazonalizada** (M/M-1);
2. **Média móvel de três meses** (MM3M) do nível;
3. **MM3M atual contra a MM3M dos três meses anteriores**.

O tipo da série define a unidade da variação:
| tipo | exemplo | unidade da variação |
|------|---------|---------------------|
| `indice` | IBC-Br, PIM, PMC, PMS | variação **%** |
| `taxa` | taxa de desocupação | diferença em **p.p.** |
| `fluxo` | saldo do CAGED | variação de **nível** (pode cruzar zero) |

## Regra de cor do bloco (`Ct`)

Calculada sobre os **indicadores de núcleo** (`nucleo: True`): IBC-Br, PIM geral,
PMC restrito, PMS, população ocupada, massa real de rendimentos e estoque de
vínculos formais.

| Difusão positiva do núcleo | Cor | `Ct` |
|---|---|---|
| ≥ 60% crescendo | 🟢 VERDE | 0 |
| 40%–60% | 🟡 AMARELO | 1 |
| < 40% (queda intensa e ampla) | 🔴 VERMELHO | 2 |
| < 40% (queda parcial/moderada) | 🟠 LARANJA | 2 |

## Fontes e mapeamento das séries

| Indicador | Fonte | Identificador |
|---|---|---|
| IBC-Br dessaz. | BCB/SGS | série `24364` |
| PIB total/ind./serv./FBCF dessaz. | IBGE/SIDRA | tab. `1621` v`584`, C11255 |
| PIM-PF (geral, transf., extrativa) | IBGE/SIDRA | tab. `8888` v`12607`, C544 |
| PIM-PF (bens capital, intermediários) | IBGE/SIDRA | tab. `8887` v`12607`, C543 |
| PMC varejo restrito (volume) | IBGE/SIDRA | tab. `8880` v`7170`, C11046=56734 |
| PMC varejo ampliado (volume) | IBGE/SIDRA | tab. `8881` v`7170`, C11046=56736 |
| PMS volume de serviços | IBGE/SIDRA | tab. `5906` v`7168`, C11046=56726 |
| População ocupada | IBGE/SIDRA | tab. `6318` v`1641`, C629=32387 |
| Taxa de desocupação | IBGE/SIDRA | tab. `6381` v`4099` |
| Massa real de rendimentos | IBGE/SIDRA | tab. `6392` v`6293` |
| Rendimento real médio | IBGE/SIDRA | tab. `6390` v`5933` |
| Estoque de vínculos formais (CAGED) | BCB/SGS | série `28763` |
| Saldo de emprego formal (CAGED) | derivado | 1ª diferença do estoque `28763` |

## Notas metodológicas e limitações

- **Cada série usa o último mês fechado disponível** na fonte, como pedem as
  Orientações. Em junho/2026, PIM e PNAD já trazem **abril**; IBC-Br, PMC e PMS
  ainda em **março** (defasagem natural de divulgação).
- **PIB é trimestral** e entra como contexto (não pesa na difusão `Ct`).
- **PNAD Contínua** é trimestre móvel e **não é dessazonalizada** pelo IBGE no
  SIDRA — tratada como tendência, não como variação dessaz. estrita.
- **CAGED**: o estoque (`28763`) é a base de núcleo do emprego (crescimento
  suave); o saldo é a 1ª diferença do estoque e é exibido como contexto, pois o
  saldo bruto é fortemente sazonal. Para o saldo dessazonalizado oficial pode-se
  trocar a fonte depois.
- A escala de cor **não é datação automática de recessão**, e sim instrumento de
  monitoramento — exatamente como ressaltam as Orientações.

## Estrutura do código

```
painel_ciclo/
├── config.py        # calendário 2026 + catálogo de séries coincidentes
├── fontes.py        # coletores BCB/SGS e IBGE/SIDRA (+ cache)
├── metricas.py      # 3 métricas + sinal por indicador + cor do bloco
├── coincidente.py   # orquestra o bloco e gera CSV/nota
├── painel_dados.py  # monta o payload (métricas + histórico) p/ o dashboard
├── dashboard.py     # app Dash (setores → indicadores → detalhe + termômetro)
├── textos.py        # fichas explicativas por indicador (página de detalhe)
├── run.py           # ponto de entrada do relatório (CLI)
├── dados/           # cache de séries brutas
└── saidas/          # CSV + nota .md por fechamento
```
