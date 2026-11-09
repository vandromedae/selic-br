"""Ferramenta web: juros e dívida pública — Brasil (2002–2026).

Streamlit reaproveitando `src/processa/indicadores.py` (núcleo analítico)
e a paleta de `src/viz/graficos.py`.

Rodar: `streamlit run app/app.py` (ambiente conda juros_divida, na raiz do repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.processa import indicadores as ind  # noqa: E402
from src.viz.graficos import CORES_DETENTOR  # noqa: E402

st.set_page_config(
    page_title="Juros e Dívida — Transparência",
    page_icon="🏦",
    layout="wide",
)

# ------------------------------------------------------------------ dados com cache


@st.cache_data(show_spinner="carregando dados processados…")
def dados() -> dict[str, pd.DataFrame]:
    j = ind.juros_anuais()
    f = ind.fatores_anuais()
    dz = ind.detentores_anuais()
    jd = ind.juros_por_detentor()
    mm = ind.selic_real_mensal()
    cm = ind.custo_medio_dpf()
    val = ind.validacao_bndes()
    return {
        "juros": j,
        "fatores": f,
        "detentores": dz,
        "juros_detentor": jd,
        "macro": mm,
        "custo": cm,
        "validacao_bndes": val,
    }


D = dados()

ORDEM_DETENTOR = [
    "Instituições Financeiras", "Fundos de Investimento", "Previdência",
    "Não-residentes", "Tesouro Direto", "Seguradoras", "Governo", "Outros",
]


def fmt_bi(v: float, casas: int = 1) -> str:
    return f"R$ {v:,.{casas}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: float, casas: int = 1) -> str:
    return f"{v:.{casas}f}%".replace(".", ",")


# ------------------------------------------------------------------ figuras


def _layout(fig, altura: int = 420, fonte: int = 12) -> None:
    fig.update_layout(
        height=altura,
        font=dict(size=fonte, family="Inter, sans-serif"),
        title_font_size=16,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=48, b=10),
        template="plotly_white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e8e8e8")
    fig.update_yaxes(showgrid=True, gridcolor="#e8e8e8")


def fig_juros_swaps() -> go.Figure:
    j = D["juros"]
    j = j[(j.ano >= 2008) & (j.ano < 2026)]
    fig = go.Figure()
    fig.add_bar(x=j.ano, y=j.juros_ex_swap_pib_pct, name="juros ex-swaps",
                marker_color="#1f77b4",
                customdata=j.swap_pp_pib,
                hovertemplate="%{x}: %{y:.2f}% do PIB<br>swap: %{customdata:+.2f} p.p.<extra></extra>")
    fig.add_bar(x=j.ano, y=j.juros_pib_pct, name="juros (incl. swaps)",
                marker_color="#7f7f7f")
    fig.add_vline(x=2024.5, line_dash="dash", line_color="#000000", opacity=0.5)
    fig.add_annotation(x=2024, y=j.juros_pib_pct.max() * 1.02,
                       text="2024: prejuízo BCB (+0,98 p.p.)", showarrow=False,
                       font=dict(size=11, color="#d62728"))
    fig.add_annotation(x=2025.5, y=6.0,
                       text="2025: ganho BCB (−0,83 p.p.)", showarrow=False,
                       font=dict(size=11, color="#2ca02c"))
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_xaxes(title="ano")
    fig.update_yaxes(title="% do PIB")
    _layout(fig)
    return fig


def fig_selic_inflacao() -> go.Figure:
    m = D["macro"]
    fig = go.Figure()
    for col, cor, nome, dash in [
        ("selic_meta", "#1f77b4", "Selic meta (fim de mês)", None),
        ("ipca_12m", "#d62728", "IPCA 12m (realizado)", None),
        ("focus_ipca_12m", "#ff7f0e", "Focus: IPCA 12m (média)", "dash"),
    ]:
        fig.add_scatter(x=m.index, y=m[col], name=nome, line=dict(color=cor, dash=dash or "solid")
                        if dash else dict(color=cor), mode="lines")
    fig.add_hline(y=4.5, line=dict(width=1), line_dash="dot", line_color="#7f7f7f")
    fig.add_annotation(x=m.index[36], y=5.3, text="meta de inflação (4,5%)",
                       showarrow=False, font=dict(size=11, color="#7f7f7f"))
    fig.update_xaxes(title="")
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_juro_real() -> go.Figure:
    m = D["macro"]
    fig = go.Figure()
    fig.add_scatter(x=m.index, y=m.juro_real_ex_ante, name="juro real ex ante (Selic − Focus)",
                    line=dict(color="#2ca02c"), mode="lines")
    fig.add_scatter(x=m.index, y=m.juro_real_ex_post, name="juro real ex post (Selic − IPCA)",
                    line=dict(color="#7f7f7f"), mode="lines")
    media = m.loc[:"2014", "juro_real_ex_ante"].mean()
    fig.add_hline(y=media, line=dict(dash="dot", color="#2ca02c"))
    fig.add_annotation(x=m.index[36], y=media + 0.6,
                       text=f"média 2002–2014: {media:.1f}%",
                       showarrow=False, font=dict(size=11, color="#2ca02c"))
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_desvio_taylor() -> go.Figure:
    t = D["macro"][["selic_meta", "focus_ipca_12m"]].dropna().copy()
    t["taylor"] = 2.5 + t.focus_ipca_12m + 0.5 * (t.focus_ipca_12m - 4.5)
    t["desvio"] = t.selic_meta - t.taylor
    fig = go.Figure()
    fig.add_scatter(x=t.index, y=t.selic_meta, name="Selic meta",
                    line=dict(color="#1f77b4"), mode="lines")
    fig.add_scatter(x=t.index, y=t.taylor, name="Regra de Taylor simples (r*=2,5; meta 4,5)",
                    line=dict(color="#7f7f7f", dash="dash"), mode="lines")
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_detentores(stacked: bool) -> go.Figure:
    ordem = [c for c in ORDEM_DETENTOR]
    fig = go.Figure()
    dez = D["detentores"]
    for detentor in ordem:
        sub = dez[dez.detentor == detentor].sort_values("data")
        fig.add_scatter(
            x=sub.data.dt.year + pd.DatetimeIndex(sub.data).month / 12,
            y=sub.participacao * 100,
            name=detentor, customdata=sub.valor_bi,
            line=dict(color=CORES_DETENTOR.get(detentor, "#999999")),
            stackgroup="um" if stacked else None, fill="tonexty" if stacked else None,
            hovertemplate="%{x:.0f}: %{y:.1f}% (R$ %{customdata:,.0f} bi)"
            "<extra>" + detentor + "</extra>",
        )
    fig.update_layout(legend=dict(orientation="h", y=-0.18, yanchor="top"))
    fig.update_yaxes(title="% do estoque DPMFi",
                     range=[0, 100] if stacked else None)
    fig.update_xaxes(title="calendário")
    _layout(fig, altura=440)
    return fig


def fig_estoque_detentor() -> go.Figure:
    dez = D["detentores"]
    ultimo = dez[dez.data == dez.data.max()].sort_values("valor_bi")
    fig = go.Figure(go.Bar(
        x=ultimo.valor_bi, y=ultimo.detentor, orientation="h",
        marker_color=[CORES_DETENTOR.get(c, "#999999") for c in ultimo.detentor],
        customdata=ultimo.participacao,
        hovertemplate="%{y}: R$ %{x:,.0f} bi (%{customdata:.1%})<extra></extra>",
    ))
    fig.update_layout(xaxis_title="R$ bilhões", yaxis_title=None)
    fig.update_traces(texttemplate="R$ %{x:,.0f} bi", textposition="outside",
                      cliponaxis=False)
    _layout(fig, altura=420)
    return fig


def fig_fluxo_juros_detentor() -> go.Figure:
    jd = D["juros_detentor"]
    jd = jd[jd.ano < 2026]
    conv = jd.pivot_table(index="ano", columns="detentor", values="juros_estimado_bi")
    fig = go.Figure()
    for detentor in [c for c in conv.columns if not conv[c].isna().all()]:
        fig.add_scatter(
            x=conv.index, y=conv[detentor], name=detentor,
            line=dict(color=CORES_DETENTOR.get(detentor, "#999999")),
            stackgroup="dois", fill="tonexty",
        )
    fig.update_yaxes(title="R$ bilhões/ano (estimado)")
    fig.update_xaxes(title="ano")
    _layout(fig, altura=440)
    return fig


def fig_cascata(ano: int = 2025) -> go.Figure:
    f = D["fatores"].set_index("ano")
    r = f.loc[ano]
    etapas = [
        ("estoque anterior", r.estoque_anterior_mi, "#1f77b4"),
        ("emissão líquida", r.emissao_liq_mi, "#2ca02c"),
        ("juros apropriados", r.juros_apropriados_mi, "#d62728"),
        ("estoque final", r.estoque_final_mi, "#1f77b4"),
    ]
    fig = go.Figure(go.Waterfall(
        x=[s[0] for s in etapas],
        measure=["absolute", "relative", "relative", "total"],
        y=[r.estoque_anterior_mi, r.emissao_liq_mi, r.juros_apropriados_mi, 0],
        textposition="outside",
        connector={"line": {"color": "#bbb"}},
        increasing={"marker": {"color": "#2ca02c"}},
        decreasing={"marker": {"color": "#d62728"}},
        totals={"marker": {"color": "#1f77b4"}},
    ))
    fig.update_layout(yaxis_title="R$ bilhões")
    _layout(fig, altura=430)
    return fig


def fig_fluxos_anuais() -> go.Figure:
    f = D["fatores"]
    f = f[(f.ano >= 2010) & (f.ano < 2026)]
    fig = go.Figure()
    for col, rotulo, cor in [
        ("juros_apropriados_mi", "juros apropriados", "#d62728"),
        ("emissao_liq_mi", "emissão líquida", "#1f77b4"),
    ]:
        fig.add_scatter(x=f.ano, y=f[col] / 1000, name=rotulo, marker_color=cor,
                        mode="lines+markers")
    fig.add_scatter(x=f.ano, y=(-f.resgates_mi) / 1000, name="resgates (amortizações + juros pagos)",
                    marker_color="#7f7f7f", mode="lines+markers", line_dash="dot")
    fig.update_yaxes(title="R$ bilhões")
    fig.update_xaxes(title="ano")
    _layout(fig)
    return fig


def fig_juros_primario() -> go.Figure:
    from src.extratores.base import ler_parquet  # noqa: E402
    sgs = ler_parquet("sgs")

    def serie(nome: str) -> pd.Series:
        return sgs[sgs.serie == nome].set_index("data")["valor"].dropna()

    jp, pp = serie("juros_pib_12m"), serie("primario_pib_12m")
    fig = go.Figure()
    fig.add_scatter(x=jp.index, y=jp, name="juros nominais % PIB (12m)",
                    line=dict(color="#d62728"), mode="lines")
    fig.add_scatter(x=pp.index, y=pp, name="resultado primário % PIB (12m)",
                    line=dict(color="#2ca02c"), mode="lines")
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    fig.update_yaxes(title="% do PIB")
    _layout(fig)
    return fig


def fig_i_g() -> go.Figure:
    v = D["juros"]
    v = v[(v.ano >= 2012) & (v.ano < 2026)].set_index("ano")
    g_nom = v.pib_mi.pct_change() * 100
    m = D["macro"]
    m_anual = m[m.ipca_12m.notna()].groupby(m[m.ipca_12m.notna()].index.year).mean()
    g_real = g_nom - m_anual.ipca_12m
    tab = pd.DataFrame({
        "g (PIB nominal)": g_nom,
        "g (PIB real aprox.)": g_real,
    }).loc[2013:]
    i_nom = D["custo"].set_index("data").taxa_pct_aa.resample("YE").last()
    i_nom.index = i_nom.index.year
    i_real = D["macro"].groupby(D["macro"].index.year).mean().juro_real_ex_ante
    tab["i (custo médio DPF)"] = i_nom.loc[2013:2025]
    tab["r (juro real ex ante)"] = i_real.loc[2013:2025]
    tab["i − g (nominal)"] = tab["i (custo médio DPF)"] - tab["g (PIB nominal)"]
    tab["r − g (real)"] = tab["r (juro real ex ante)"] - tab["g (PIB real aprox.)"]
    tab.index.name = "ano"
    tab_l = tab.reset_index()
    cores = ["#2ca02c" if x >= 0 else "#d62728" for x in tab_l["i − g (nominal)"]]
    fig = go.Figure()
    fig.add_bar(x=tab_l.ano, y=tab_l["i − g (nominal)"], name="i − g (nominal)",
                marker_color=cores)
    fig.add_bar(x=tab_l.ano, y=tab_l["r − g (real)"], name="r − g (real)",
                marker_color=["#2ca02c" if x >= 0 else "#ff7f0e" for x in tab_l["r − g (real)"]])
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    fig.update_yaxes(title="% a.a.")
    fig.update_xaxes(title="ano")
    _layout(fig)
    return tab, fig


def fig_mandatos() -> pd.DataFrame:
    m = D["macro"]
    mandatos = [
        ("Lula 1-2 (03-10)", "2003-01-01", "2010-12-31"),
        ("Dilma/Temer (11-18)", "2011-01-01", "2018-12-31"),
        ("Bolsonaro (19-22)", "2019-01-01", "2022-12-31"),
        ("Lula 3 (23-26)", "2023-01-01", "2026-12-31"),
    ]
    linhas = []
    for nome, ini, fim in mandatos:
        rec = m.loc[ini: fim, "juro_real_ex_ante"].dropna()
        linhas.append({"mandato": nome, "juro_real_ex_ante_medio": rec.mean(),
                       "máximo": rec.max()})
    return pd.DataFrame(linhas).set_index("mandato")


# ------------------------------------------------------------------ UI

st.sidebar.title("🏦 Juros e dívida pública")
st.sidebar.caption("Brasil, 2002–2026 · apenas fontes públicas")

PAGINA = st.sidebar.radio(
    "Pergunta",
    [
        "Visão geral",
        "P1 · Os juros se justificam?",
        "P2 · Quem recebe os juros?",
        "P3 · Os juros amortizam a dívida?",
        "P4 · Os juros geram capital produtivo?",
        "P5 · Houve propositalidade?",
        "Transparência: lacunas",
        "Fontes e metodologia",
    ],
    label_visibility="collapsed",
)
st.sidebar.divider()

j = D["juros"]
ultimo_ano_completo = j[j.ano < 2026].ano.max()
row = j[j.ano == ultimo_ano_completo].iloc[0]
cm_ult = D["custo"].data.max()
cm_val = D["custo"].set_index("data").taxa_pct_aa.loc[cm_ult]
m_ult = D["macro"].index.max()
dez_ult = D["detentores"].data.max()

with st.sidebar.expander("📌 números-chave", expanded=True):
    st.markdown(f"""
**Juros nominais ({ultimo_ano_completo}):** {fmt_bi(row.juros_mi / 1000)}
· {fmt_pct(row.juros_pib_pct)} do PIB

**Swaps ({ultimo_ano_completo}):** {row.swap_pp_pib:+.2f} p.p. do PIB
({"aumentam" if row.swap_pp_pib > 0 else "reduzem"} os juros)

**Custo médio DPF:** {fmt_pct(cm_val)} a.a. ({cm_ult:%m/%Y})

**Selic meta:** {fmt_pct(D["macro"].loc[m_ult].selic_meta)} a.a.
({m_ult:%m/%Y}) · **IPCA 12m:** {fmt_pct(D["macro"].loc[m_ult].ipca_12m)}

**Estoque DPMFi:** {fmt_bi(D["detentores"][D["detentores"].data == dez_ult].valor_bi.sum(), 0)}
({dez_ult:%m/%Y})
""")

st.sidebar.divider()
st.sidebar.caption(
    "Análise de dados, não posicionamento. A tese de “propositalidade” "
    "(P5) exige documentos — fase posterior. Nomes de credores "
    "individuais não são públicos (Req. 696/2019 negado)."
)

# ============================================================ páginas

if PAGINA == "Visão geral":
    st.title("Visão geral")
    st.markdown(
        "Uma base de dados própria, construída de **fontes primárias "
        "(BCB/SGS, Tesouro/RMD, Focus/Olinda, IBGE/SIDRA)**, validada "
        "externamente e organizada para responder as cinco perguntas "
        "desta pesquisa — ver a aba **Fontes e metodologia**."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Juros nominais {ultimo_ano_completo}",
              fmt_bi(row.juros_mi / 1000), f"{fmt_pct(row.juros_pib_pct)} do PIB")
    c2.metric("Efeito swaps", f"{row.swap_pp_pib:+.2f} p.p.",
              "aumenta" if row.swap_pp_pib > 0 else "reduz")
    c3.metric("Custo médio DPF", f"{cm_val:.2f}% a.a.".replace(".", ","),
              f"dez/20: {cm_ult:%m/%Y}")
    c4.metric("Estoque DPMFi", fmt_bi(D["detentores"][D["detentores"].data == dez_ult].valor_bi.sum(), 0))

    st.plotly_chart(fig_juros_swaps(), use_container_width=True)
    st.markdown(
        "**Validação BNDES** — o cálculo próprio reproduz o Estudo BNDES 67/2026 "
        "com desvio ≤ 0,03 p.p. (ver notebook 00 ou a tabela na parte inferior):"
    )
    st.dataframe(D["validacao_bndes"], use_container_width=True, hide_index=True)

elif PAGINA.startswith("P1"):
    st.title("P1 · Os juros altos se justificam?")
    st.markdown(
        "A Selic acompanha a inflação **esperada** (Focus), não realizada. O "
        "que é excepcional é a magnitude: juro real ex ante de 2024–2026 em "
        "~8–9 p.p. com inflação **dentro da meta**."
    )
    st.plotly_chart(fig_selic_inflacao(), use_container_width=True)
    st.plotly_chart(fig_juro_real(), use_container_width=True)
    st.plotly_chart(fig_desvio_taylor(), use_container_width=True)
    st.info(
        "**Conclusão verificável:** o juro extra atual não é “preço da "
        "inflação”: é um prêmio institucional adicional. Defender que "
        "“está justificado” é uma posição — a causa adicional (risco fiscal? "
        "credibilidade?) não está nos dados macro aqui usados."
    )

elif PAGINA.startswith("P2"):
    st.title("P2 · Quem recebe os juros?")
    st.markdown(
        "Composição de estoque por grupo de detentor (RMD 2.7) e **estimativa** "
        "do fluxo de juros por grupo (juros do ano × participação em dezembro)."
    )
    st.plotly_chart(fig_detentores(stacked=True), use_container_width=True)
    cols = st.columns(2)
    with cols[0]:
        st.plotly_chart(fig_estoque_detentor(), use_container_width=True)
    with cols[1]:
        st.plotly_chart(fig_fluxo_juros_detentor(), use_container_width=True)
    st.warning(
        "**Estimativa, não dado oficial:** participação em dezembro × juros "
        "anuais. A União não publica fluxo por credor. Identificar "
        "instituições dentro do grupo não é possível (sigilo; Req. 696/2019 "
        "negado) — ver aba **Transparência: lacunas**."
    )

elif PAGINA.startswith("P3"):
    st.title("P3 · Os juros amortizam a dívida?")
    st.markdown(
        "Identidade dos fatores de variação da DPF (Tesouro, anexo 2.9): "
        "emissões ≈ resgates + juros — os juros **não amortizam** a dívida; "
        "**os juros são a dívida nova**."
    )
    f_ano = st.slider("ano da cascata", 2012, 2025, 2025, key="cascata")
    st.plotly_chart(fig_cascata(f_ano), use_container_width=True)
    st.plotly_chart(fig_fluxos_anuais(), use_container_width=True)
    t = D["fatores"].copy()
    t = t[(t.ano >= 2012) & (t.ano < 2026)]
    t["emissoes_mult_juros"] = t.emissoes_mi / t.juros_apropriados_mi
    st.dataframe(
        t[["ano", "emissoes_mi", "resgates_mi", "juros_apropriados_mi",
           "emissoes_mult_juros"]].assign(
            **{"emissoes (R$ bi)": lambda x: (x.emissoes_mi / 1000).round(0),
               "resgates (R$ bi)": lambda x: (x.resgates_mi / -1000).round(0),
               "juros (R$ bi)": lambda x: (x.juros_apropriados_mi / 1000).round(0)}
        )[["ano", "emissoes (R$ bi)", "resgates (R$ bi)", "juros (R$ bi)",
           "emissoes_mult_juros"]].round(2),
        use_container_width=True, hide_index=True,
    )
    st.plotly_chart(fig_juros_primario(), use_container_width=True)
    st.info("Equação honesta para o público: **os juros não reduzem a dívida — "
            "eles são a dívida nova** (mais a dívida que chega próxima).")

elif PAGINA.startswith("P4"):
    st.title("P4 · Os juros geram capital produtivo?")
    st.markdown(
        "**i > g quase sempre desde 2012** (exceção: choque inflacionário de "
        "2021–22) e **r > g real desde 2022**: a dívida se auto-alimenta e o "
        "capital migra do crédito/investimento para o título soberano."
    )
    tab, fig = fig_i_g()
    c1, c2 = st.columns([2, 3])
    with c1:
        st.dataframe(tab.round(1), use_container_width=True)
    with c2:
        st.plotly_chart(fig, use_container_width=True)
    st.info(
        "Nos dados públicos de fluxo **não há caminho pelo qual o dispêndio "
        "de juros se converta em investimento produtivo**: é rolagem (P3) + "
        "transferência a detentores (P2). O soberano rendendo juro real alto "
        "sem risco “rouba” a poupança do crédito privado."
    )

elif PAGINA.startswith("P5"):
    st.title("P5 · O aumento foi proposital?")
    st.markdown(
        "O que os dados mostram: a régua de juro real **alternou de forma "
        "dramática e reversível** entre mandatos — não é fatalidade técnica. "
        "**Não é afirmação de intenção**: isso exige documentos (atas, "
        "manifestos, ofícios) — fase posterior."
    )
    tab = fig_mandatos()
    st.bar_chart(tab["juro_real_ex_ante_medio"], color="#1f77b4", height=340)
    st.dataframe(tab.round(1), use_container_width=True)

    j2 = j[j.ano >= 2002]
    st.caption(
        f"Dispêndio nominal com juros: {fmt_bi(j2.juros_mi.iloc[0] / 1000, 0)} "
        f"({j2.ano.iloc[0]}) → {fmt_bi(j2[j2.ano < 2026].juros_mi.iloc[-1] / 1000, 0)} "
        f"({ultimo_ano_completo}) — sem contar o efeito dos swaps."
    )
    st.plotly_chart(fig_juros_swaps(), use_container_width=True)
    st.info(
        "Um país que praticou **2% de juro real** em 2021 praticou **9%** em "
        "2025 sem mudança da estrutura produtiva: o patamar é *escolha de "
        "política*. Quem defende que “não havia alternativa” precisa "
        "apontar por que ela praticamente inverteu de 2022 para cá."
    )

elif PAGINA == "Transparência: lacunas":
    st.title("O que NÃO é público (e por quê)")
    st.markdown(
        "Esta ferramenta mostra tudo que é possível mostrar com dados "
        "públicos — e **declara explicitamente** o que não é público:"
    )
    lacunas = [
        {
            "lacuna": "Quem (nome/instituição) recebe quanto de juros",
            "estado": "**Negado.** Requerimento 696/2019 (Câmara dos "
                      "Deputados) pedia a lista ao STN; resposta foi "
                      "negativa por **sigilo bancário**.",
            "o que há": "Estimativa por grupo: participação de dezembro × "
                        "juros nominais anuais (aba P2).",
        },
        {
            "lacuna": "Fluxo de juros por detentor (dado oficial)",
            "estado": "**Não existe.** O Tesouro publica juros agregados "
                      "(SGS 4616); por detentor só o estoque "
                      "(RMD 2.7), mensal, por grupo.",
            "o que há": "Estimativa própria — marcada como tal em toda "
                        "a interface.",
        },
        {
            "lacuna": "Desemprego 2002–2011 (série comparável)",
            "estado": "**Não existe.** A PNAD-C começou em 2012; antes só "
                      "PNAD anual/mensal incomparável.",
            "o que há": "Série desde 2012, com a lacuna informada nos "
                        "gráficos que a usam.",
        },
        {
            "lacuna": "API do Portal da Transparência",
            "estado": "**Exige chave de API** (o pedido via LAI foi "
                      "cancelado/deferido com exigência de credencial); "
                      "dispensada neste projeto — substituída por SGS 4616 "
                      "+ fatores de variação da DPF.",
            "o que há": "Mesmo resultado analítico pelas séries do BCB/Tesouro.",
        },
        {
            "lacuna": "Contratos de swap por contraparte",
            "estado": "**Agregado**. O BCB publica o resultado caixa total "
                      "(SGS 29522), não o desmembrado por banco.",
            "o que há": "A contribuição anual dos swaps para os juros "
                        "(p.p. do PIB) — ver Visão geral.",
        },
    ]
    for l in lacunas:
        with st.expander(f"🔒 {l['lacuna']}"):
            st.markdown(f"**Estado atual:** {l['estado']}")
            st.markdown(f"**O que a ferramenta oferece no lugar:** {l['o que há']}")
    st.success(
        "Para abrir de fato a identificação dos credores, seria necessário "
        "um ato legal/regulatório sobre titularidade junto aos custodiantes "
        "(SELIC/Cetip) — a ferramenta indica isto como caminho, não como "
        "afirmação."
    )

else:
    st.title("Fontes e metodologia")
    st.markdown("""
| Fonte | Uso nesta ferramenta |
| --- | --- |
| **BCB/SGS** (25 séries) | juros nominais (4616), swaps caixa (29522), PIB nominal (4380), Selic/IPCA, primário |
| **Tesouro/STN — RMD** | detentores (Anexo 2.7), custo médio (4.1–4.3), composição (5.5) |
| **Tesouro/STN — fatores DPF (Anexo 2.9)** | estoque, emissões, resgates, juros apropriados |
| **Focus / Olinda (BCB)** | IPCA-12m e Selic anuais (medianas) |
| **IBGE SIDRA 6381** | desemprego PNAD-C (desde 2012) |
| **BNDES Estudo 67/2026** | referência externa de validação |

**Regras declaradas:**

1. **Fluxo de juros por detentor é estimativa** (participação dez × juros
   anuais) — não dado oficial.
2. **Nomes de credores não são públicos** (Req. 696/2019 negado por sigilo).
3. **Desemprego** só a partir de 2012 — lacuna informada, não escondida.
4. **2026 é ano incompleto** nas séries de fluxo — o app o exclui dos
   gráficos anuais fechados e avisa.
5. Swaps: `juros_ex_swap = juros + resultado_caixa` (prejuízo do BCB aumenta
   juros; ganho reduz) — validado contra BNDES 67/2026 (desvio ≤ 0,03 p.p.).

**Notebooks completos:** `notebooks/00_validacao.ipynb` …
`05_proposital.ipynb` (executados, com saída). O núcleo analítico é
`src/processa/indicadores.py`; os extratores (com cache) em `src/extratores/`.
""")
