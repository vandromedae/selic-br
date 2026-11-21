"""Figuras Plotly do app (recebem os dados carregados)."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import plotly.graph_objects as go

from src.processa import indicadores as ind
from src.viz.graficos import CORES_DETENTOR

from app.dados import ANO_CORTE

# ordem de exibição dos grupos de detentor (RMD 2.7)
ORDEM_DETENTOR = [
    "Instituições Financeiras", "Fundos de Investimento", "Previdência",
    "Não-residentes", "Tesouro Direto", "Seguradoras", "Governo", "Outros",
]

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


def fig_juros_swaps(d) -> go.Figure:
    j = d["juros"]
    j = j[(j.ano >= 2008) & (j.ano < ANO_CORTE)]
    fig = go.Figure()
    fig.add_bar(x=j.ano, y=j.juros_ex_swap_pib_pct, name="juros ex-swaps",
                marker_color="#1f77b4",
                customdata=j.swap_pp_pib,
                hovertemplate="%{x}: %{y:.2f}% do PIB<br>swap: %{customdata:+.2f} p.p.<extra></extra>")
    fig.add_bar(x=j.ano, y=j.juros_pib_pct, name="juros (incl. swaps)",
                marker_color="#7f7f7f")
    fig.add_vline(x=2024.5, line_dash="dash", line_color="#000000", opacity=0.5)
    # anotações derivadas de swap_pp_pib (valores calculados, não fixos)
    for xpos, ybase, ano in [(2024, j.juros_pib_pct.max() * 1.02, 2024),
                             (2025.5, 6.0, 2025)]:
        val = float(j.loc[j.ano == ano, "swap_pp_pib"].iloc[0])
        rot = "prejuízo" if val > 0 else "ganho"
        pp = f"{val:+.2f}".replace(".", ",")
        fig.add_annotation(
            x=xpos, y=ybase, showarrow=False,
            text=f"{ano}: {rot} BCB ({pp} p.p.)",
            font=dict(size=11, color="#d62728" if val > 0 else "#2ca02c"),
        )
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_xaxes(title="ano")
    fig.update_yaxes(title="% do PIB")
    _layout(fig)
    return fig


def fig_selic_inflacao(d) -> go.Figure:
    m = d["macro"]
    fig = go.Figure()
    for col, cor, nome, dash in [
        ("selic_meta", "#1f77b4", "Selic meta (fim de mês)", None),
        ("ipca_12m", "#d62728", "IPCA 12m (realizado)", None),
        ("focus_ipca_12m", "#ff7f0e", "Focus: IPCA 12m (média)", "dash"),
    ]:
        fig.add_scatter(x=m.index, y=m[col], name=nome, line=dict(color=cor, dash=dash or "solid")
                        if dash else dict(color=cor), mode="lines")
    fig.add_scatter(x=m.index, y=ind.meta_inflacao(), name="meta de inflação (4,5% até 2024; 3,0% desde 2025)",
                    line=dict(color="#7f7f7f", dash="dot", width=1), mode="lines")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_juro_real(d) -> go.Figure:
    m = d["macro"]
    fig = go.Figure()
    fig.add_scatter(x=m.index, y=m.juro_real_ex_ante, name="juro real ex ante (Selic − Focus)",
                    line=dict(color="#2ca02c"), mode="lines")
    fig.add_scatter(x=m.index, y=m.juro_real_ex_post, name="juro real ex post (Selic − IPCA)",
                    line=dict(color="#7f7f7f"), mode="lines")
    media = m.loc[:"2014", "juro_real_ex_ante"].mean()
    fig.add_hline(y=media, line=dict(dash="dot", color="#2ca02c"))
    fig.add_annotation(x=pd.Timestamp("2005-01-31"), y=media + 0.6,
                       text=f"média 2002–2014: {media:.1f}%",
                       showarrow=False, font=dict(size=11, color="#2ca02c"))
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_desvio_taylor(d) -> go.Figure:
    t = d["macro"][["selic_meta", "focus_ipca_12m"]].dropna().copy()
    # meta VARIÁVEL (4,5% até 2024; 3,0% desde 2025): com a meta antiga, o
    # Taylor de 2025–26 fica 0,75 p.p. abaixo e o desvio infla na mesma medida
    meta = ind.meta_inflacao().reindex(t.index).ffill()
    t["taylor"] = 2.5 + t.focus_ipca_12m + 0.5 * (t.focus_ipca_12m - meta)
    # r* é premissa, não dado: o desvio cai 1:1 com r* — a régua com r*=5
    # (limite superior da faixa) fica 2,5 p.p. acima da base
    t["taylor_r5"] = 5 + t.focus_ipca_12m + 0.5 * (t.focus_ipca_12m - meta)
    fig = go.Figure()
    fig.add_scatter(x=t.index, y=t.taylor,
                    name="Regra de Taylor simples (r*=2,5; meta 4,5→3,0)",
                    line=dict(color="#7f7f7f", dash="dash"), mode="lines")
    # faixa entre a regra e a Selic = desvio da política em relação à regra
    fig.add_scatter(x=t.index, y=t.selic_meta, name="Selic meta",
                    line=dict(color="#1f77b4"), mode="lines",
                    fill="tonexty", fillcolor="rgba(31,119,180,0.15)")
    fig.add_scatter(x=t.index, y=t.taylor_r5, name="Taylor com r*=5 (sensibilidade)",
                    line=dict(color="#7f7f7f", dash="dot"), mode="lines")
    fig.update_yaxes(title="% a.a.")
    _layout(fig)
    return fig


def fig_detentores(d, stacked: bool) -> go.Figure:
    ordem = [c for c in ORDEM_DETENTOR]
    fig = go.Figure()
    dez = d["detentores"]
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


def fig_estoque_detentor(d) -> go.Figure:
    dez = d["detentores"]
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


def fig_fluxo_juros_detentor(d) -> go.Figure:
    jd = d["juros_detentor"]
    jd = jd[jd.ano < ANO_CORTE]
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


def fig_cascata(d, ano: int = 2025) -> go.Figure:
    f = d["fatores"].set_index("ano")
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


def fig_fluxos_anuais(d) -> go.Figure:
    f = d["fatores"]
    f = f[(f.ano >= 2010) & (f.ano < ANO_CORTE)]
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


def fig_juros_primario(d) -> go.Figure:
    sp = ind.juros_primario_12m()
    fig = go.Figure()
    fig.add_scatter(x=sp.index, y=sp.juros_pib_12m,
                    name="juros nominais % PIB (12m)",
                    line=dict(color="#d62728"), mode="lines")
    fig.add_scatter(x=sp.index, y=sp.primario_pib_12m,
                    name="primário % PIB (12m) — positivo = déficit",
                    line=dict(color="#2ca02c"), mode="lines")
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    fig.update_yaxes(title="% do PIB")
    _layout(fig)
    return fig
