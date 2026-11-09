"""Séries derivadas (anuais e mensais) consumidas pelas análises P1–P5.

Tudo aqui é derivado dos parquets de `dados/processado/` — nenhum download.
"""

from __future__ import annotations

import pandas as pd

from ..extratores.base import ler_parquet

ANO_INICIO = 2002


# ------------------------------------------------------------------ fiscal/anual


def juros_anuais() -> pd.DataFrame:
    """Juros nominais federais (SGS 4616) com decomposição por swap e % PIB.

    Colunas: ano, juros_mi, swap_resultado_mi, juros_ex_swap_mi, pib_mi,
             swap_pp_pib, juros_pib_pct, juros_ex_swap_pib_pct
    """
    sgs = ler_parquet("sgs")

    def _serie(nome: str) -> pd.Series:
        s = sgs[sgs.serie == nome].set_index("data")["valor"]
        return s.resample("YE").sum()

    juros = _serie("juros_mensal")
    swap = _serie("swap_resultado_caixa")  # caixa negativa = prejuízo = juros maiores
    pib = _serie("pib_nominal_mensal")

    df = pd.DataFrame({
        "juros_mi": juros,
        "swap_resultado_mi": swap,
        "pib_mi": pib,
    })
    df["ano"] = df.index.year
    # resultado caixa de swap negativo = prejuízo do BCB = aumenta o dispêndio
    # com juros; positivo (ganho) reduz. Logo: juros_ex = juros + resultado.
    df["juros_ex_swap_mi"] = df["juros_mi"] + df["swap_resultado_mi"]
    # contribuição dos swaps para juros/PIB (+ aumenta, - reduz), p.p.
    df["swap_pp_pib"] = -100 * df["swap_resultado_mi"] / df["pib_mi"]
    df["juros_pib_pct"] = 100 * df["juros_mi"] / df["pib_mi"]
    df["juros_ex_swap_pib_pct"] = 100 * df["juros_ex_swap_mi"] / df["pib_mi"]
    df = df[df.ano >= ANO_INICIO - 1].reset_index(drop=True)
    return df


def fatores_anuais() -> pd.DataFrame:
    """Fatores de variação da DPF (Tesouro, anexo 2.9) em R$ milhões."""
    fat = ler_parquet("tesouro_fatores")
    anual = fat[fat.periodo == "anual"].copy()
    anual["ano"] = anual.data.dt.year
    chave = {
        "Estoque anterior1": "estoque_anterior_mi",
        "Estoque mês em análise": "estoque_final_mi",
        "Variação Nominal": "variacao_mi",
        "I.1.1 - Emissões": "emissoes_mi",
        "I.1.2 - Resgates": "resgates_mi",
        "I.2 - Juros  Apropriados": "juros_apropriados_mi",
    }
    piv = anual[anual.fator.isin(chave)].pivot_table(
        index="ano", columns="fator", values="valor_mi", aggfunc="first")
    piv = piv.rename(columns=chave)
    piv["emissao_liq_mi"] = piv["emissoes_mi"] + piv["resgates_mi"]  # resgates < 0
    return piv.reset_index()


def detentores_anuais() -> pd.DataFrame:
    """Estoque da DPMFi por detentor no dezembro de cada ano (R$ bi e participação)."""
    det = ler_parquet("rmd_detentores")
    det = det[det.detentor != "Total"].copy()
    dez = det[det.data.dt.month == 12].copy()
    dez["ano"] = dez.data.dt.year
    return dez[["ano", "data", "detentor", "valor_bi", "participacao"]].reset_index(drop=True)


def detentores_mes() -> pd.DataFrame:
    det = ler_parquet("rmd_detentores")
    return det[det.detentor != "Total"].copy()


def juros_por_detentor(ano: int | None = None) -> pd.DataFrame:
    """Estimativa do fluxo de juros por detentor = participação × juros nominais.

    Premissa: participação do estoque em dezembro aproxima a participação média
    do ano no dispêndio com juros (proxy — não é dado oficial por detentor).
    """
    j = juros_anuais()
    if ano is not None:
        j = j[j.ano == ano]
    det = detentores_anuais()
    det = det.merge(j[["ano", "juros_mi"]], on="ano")
    det["juros_estimado_mi"] = det.participacao * det["juros_mi"]
    det["juros_estimado_bi"] = det.juros_estimado_mi / 1000
    return det


# ----------------------------------------------------------------- macro/mensal


def macro_mensal() -> pd.DataFrame:
    """Selic meta, IPCA 12m, IBC-Br var. 12m, desemprego e Focus 12m (mês a mês)."""
    sgs = ler_parquet("sgs")

    def _ult_do_mes(nome: str) -> pd.Series:
        s = sgs[sgs.serie == nome].set_index("data")["valor"]
        return s.resample("ME").last()

    selic_meta = _ult_do_mes("meta_selic_copom")
    ipca12 = _ult_do_mes("ipca_12m")
    ibc = _ult_do_mes("ibcbr_dessaz")
    ibc12 = (ibc / ibc.shift(12) - 1) * 100
    selic_mensal = _ult_do_mes("selic_mensal_anualizada")

    des = ler_parquet("desemprego").set_index("data")["taxa_pct"]

    foc = ler_parquet("focus_inflacao12m")
    foc = foc[foc.suavizada == "N"].set_index("data_pesquisa")["media"]
    foc = foc.resample("ME").last()

    df = pd.DataFrame({
        "selic_meta": selic_meta,
        "selic_mensal": selic_mensal,
        "ipca_12m": ipca12,
        "focus_ipca_12m": foc,
        "ibcbr_var12m": ibc12,
        "desemprego": des,
    })
    return df[df.index >= f"{ANO_INICIO}-01-31"]


def selic_real_mensal() -> pd.DataFrame:
    """Juro real ex-post (Selic mensal anualizada − IPCA 12m) e ex-ante (− Focus)."""
    m = macro_mensal()
    m["juro_real_ex_post"] = m["selic_mensal"] - m["ipca_12m"]
    m["juro_real_ex_ante"] = m["selic_mensal"] - m["focus_ipca_12m"]
    return m


def focus_anuais() -> pd.DataFrame:
    return ler_parquet("focus_anuais")


# ------------------------------------------------------------------ custo médio


def custo_medio() -> pd.DataFrame:
    c = ler_parquet("rmd_custo_medio")
    return c


def custo_medio_dpf() -> pd.DataFrame:
    """Custo médio do estoque (% a.a.), escopo DPF — série mensal desde 2005."""
    c = ler_parquet("rmd_custo_medio")
    d = c[(c.tabela == "estoque mensal") & (c.escopo == "DPF")]
    return d[["data", "taxa_pct_aa"]].reset_index(drop=True)


# --------------------------------------------------------------- validação BNDES


def validacao_bndes() -> pd.DataFrame:
    """Tabela: juros % PIB com/sem swap vs valores do Estudo BNDES 67/2026."""
    j = juros_anuais()
    esperado = {  # BNDES (2026): Gráficos 1 e 2
        2024: {"com": 8.1, "ex": 7.1},
        2025: {"com": 7.9, "ex": 8.7},
    }
    linhas = []
    for ano, esp in esperado.items():
        r = j[j.ano == ano].iloc[0]
        linhas.append({
            "ano": ano,
            "juros_pib_calc": round(r.juros_pib_pct, 2),
            "juros_pib_bndes": esp["com"],
            "ex_swap_calc": round(r.juros_ex_swap_pib_pct, 2),
            "ex_swap_bndes": esp["ex"],
            "swap_pp_calc": round(r.swap_pp_pib, 2),
        })
    return pd.DataFrame(linhas)
