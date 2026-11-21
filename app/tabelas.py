"""Tabelas, formatação e resumos do app."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import plotly.graph_objects as go

from src.processa import indicadores as ind

from app.dados import ANO_CORTE
from app.graficos import _layout

def fmt_bi(v: float, casas: int = 1) -> str:
    return f"R$ {v:,.{casas}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: float, casas: int = 1) -> str:
    return f"{v:.{casas}f}%".replace(".", ",")


def resumo(d) -> dict:
    """Números-chave derivados dos dados (sidebar e páginas)."""
    j = d["juros"]
    ultimo_ano_completo = j[j.ano < ANO_CORTE].ano.max()
    row = j[j.ano == ultimo_ano_completo].iloc[0]
    cm_ult = d["custo"].data.max()
    cm_val = d["custo"].set_index("data").taxa_pct_aa.loc[cm_ult]
    # último mês COM dado de IPCA 12m (o índice máximo do macro pode estar
    # à frente com NaN — a sidebar não pode exibir "IPCA 12m: nan%")
    m_ult = d["macro"]["ipca_12m"].dropna().index.max()
    return {
        "ultimo_ano_completo": ultimo_ano_completo,
        "row": row,
        "cm_ult": cm_ult,
        "cm_val": cm_val,
        "m_ult": m_ult,
        "dez_ult": d["detentores"].data.max(),
    }


def fig_i_g(d) -> tuple[pd.DataFrame, go.Figure]:
    v = d["juros"]
    v = v[(v.ano >= 2012) & (v.ano < ANO_CORTE)].set_index("ano")
    g_nom = v.pib_mi.pct_change() * 100
    m = d["macro"]
    m_anual = m[m.ipca_12m.notna()].groupby(m[m.ipca_12m.notna()].index.year).mean()
    # g real = PIB real do IBGE (SIDRA, volume) — não "nominal − IPCA",
    # aproximação com erro de ~1 p.p. na média (até ~5 p.p. em anos de choque)
    g_real = ind.crescimento_pib_real()
    g_real = g_real[g_real.index < ANO_CORTE]  # ano incompleto fora (regra 4)
    tab = pd.DataFrame({
        "g (PIB nominal)": g_nom,
        "g (PIB real, IBGE)": g_real,
    }).loc[2013:]
    i_nom = ind.custo_medio_dpf(tabela="estoque 12m").set_index("data").taxa_pct_aa.resample("YE").last()
    i_nom.index = i_nom.index.year
    i_real = d["macro"].groupby(d["macro"].index.year).mean().juro_real_ex_ante
    tab["i (custo médio DPF, 12m)"] = i_nom.loc[2013:2025]
    tab["r (juro real ex ante)"] = i_real.loc[2013:2025]
    tab["i − g (nominal)"] = tab["i (custo médio DPF, 12m)"] - tab["g (PIB nominal)"]
    tab["r − g (real)"] = tab["r (juro real ex ante)"] - tab["g (PIB real, IBGE)"]
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


MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]


def df_mandatos(d) -> pd.DataFrame:
    """Média e máximo do juro real ex ante por mandato (Lula 3: até a última data)."""
    m = d["macro"]
    ult = m["juro_real_ex_ante"].dropna().index.max()
    mandatos = [
        ("Lula 1-2 (03-10)", "2003-01-01", "2010-12-31"),
        ("Dilma/Temer (11-18)", "2011-01-01", "2018-12-31"),
        ("Bolsonaro (19-22)", "2019-01-01", "2022-12-31"),
        (f"Lula 3 (jan/23–{MESES_PT[ult.month - 1]}/{ult:%y})", "2023-01-01", ult),
    ]
    linhas = []
    for nome, ini, fim in mandatos:
        rec = m.loc[ini: fim, "juro_real_ex_ante"].dropna()
        linhas.append({"mandato": nome, "juro_real_ex_ante_medio": rec.mean(),
                       "máximo": rec.max()})
    return pd.DataFrame(linhas).set_index("mandato")
