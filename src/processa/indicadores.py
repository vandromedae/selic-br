"""Séries derivadas (anuais e mensais) consumidas pelas análises P1–P5.

Tudo aqui é derivado dos parquets de `dados/processado/` — nenhum download.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..extratores.base import ler_parquet

ANO_INICIO = 2002
COBERTURA_DETENTORES = 2007  # RMD 2.7 (detentores da DPMFi) começa em jan/2007

# regime de metas de inflação do BCB: até 2024, meta de 4,5% ao ano; desde
# 2025, meta de 3,0% contínua. Em ambos, faixa de tolerância de ±1,5 p.p.
# (teto = meta + 1,5: 6,0 até 2018 com ±2,0; 4,5 desde 2019)
META_ATE_2024 = 4.5
META_DESDE_2025 = 3.0
TOLERANCIA_META = 1.5


def meta_inflacao() -> pd.Series:
    """Meta de inflação do BCB, mês a mês (4,5% até 2024; 3,0% desde 2025)."""
    m = macro_mensal()
    meta = pd.Series(META_ATE_2024, index=m.index)
    meta[meta.index >= "2025-01-01"] = META_DESDE_2025
    meta.name = "meta"
    return meta


# ------------------------------------------------------------------ validação
# Falha ruidosa em vez de saída incompleta em silêncio: o dado de entrada
# precisa ter as colunas, as séries e a cobertura temporal que as contas
# assumem (mesmo padrão de fatores_anuais).


def _exigir_colunas(df: pd.DataFrame, colunas: list[str], fonte: str) -> None:
    """Falha ruidosa se colunas esperadas faltarem no dado de entrada."""
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise ValueError(
            f"{fonte}: colunas ausentes {faltando} — "
            f"encontradas: {sorted(df.columns)}")


def _sgs_serie(sgs: pd.DataFrame, nome: str) -> pd.DataFrame:
    """Fatia do SGS por nome de série; falha ruidosa se ela não existir.

    (Série ausente viraria coluna inteira de NaN no resample — falha
    silenciosa, o pior tipo para uma série analítica.)
    """
    _exigir_colunas(sgs, ["serie", "data", "valor"], "sgs.parquet")
    d = sgs[sgs.serie == nome]
    if d.empty:
        raise ValueError(
            f"sgs.parquet: série {nome!r} ausente — "
            f"disponíveis: {sorted(sgs.serie.unique())}")
    return d


def _exigir_cobertura_anual(df: pd.DataFrame, desde: int, fonte: str,
                            col_ano: str = "ano") -> None:
    """Falha ruidosa se a série anual recuar antes de `desde` ou tiver buracos."""
    if df.empty:
        raise ValueError(f"{fonte}: saiu vazia")
    anos = sorted(df[col_ano].unique())
    if anos[0] > desde:
        raise ValueError(
            f"{fonte}: cobertura recuou — primeiro ano {anos[0]} "
            f"(esperado desde {desde})")
    buracos = [a for a in range(anos[0], anos[-1] + 1) if a not in set(anos)]
    if buracos:
        raise ValueError(f"{fonte}: anos faltando na sequência: {buracos}")


# ------------------------------------------------------------------ fiscal/anual


def juros_anuais() -> pd.DataFrame:
    """Juros nominais do setor público consolidado (SGS 4616 — União,
    estados, estatais e BCB; não só os federais) com decomposição por swap
    e % PIB.

    Colunas: ano, juros_mi, swap_resultado_mi, juros_ex_swap_mi, pib_mi,
             swap_pp_pib, juros_pib_pct, juros_ex_swap_pib_pct

    `swap_resultado_mi`, `juros_ex_swap_*` e `swap_pp_pib` são NaN em
    2002–07: o SGS 29522 (resultado caixa de swap) só começa em 2008.
    """
    sgs = ler_parquet("sgs")

    def _serie(nome: str) -> pd.Series:
        s = _sgs_serie(sgs, nome).set_index("data")["valor"]
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
    df = df[df.ano >= ANO_INICIO].reset_index(drop=True)
    _exigir_cobertura_anual(df, ANO_INICIO, "juros_anuais")
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
    # Validação: o pivot por rótulo exato falha em silêncio se a STN renomear
    # um rótulo (coluna some) ou mudar só em parte do período (NaN por ano).
    faltantes = [k for k in chave if k not in piv.columns]
    if faltantes:
        achados = sorted(anual.fator.unique())
        raise ValueError(
            "fatores_anuais: rótulos do anexo 2.9 não encontrados no pivot:\n"
            + "\n".join(f"  esperado: {k!r}" for k in faltantes)
            + "\nrótulos presentes no arquivo:\n  " + "\n  ".join(map(repr, achados)))
    piv = piv.rename(columns=chave)
    nan_por_ano = piv[piv.isna().any(axis=1)]
    if not nan_por_ano.empty:
        cols = sorted(nan_por_ano.columns[nan_por_ano.isna().any()])
        raise ValueError(
            "fatores_anuais: valores ausentes após o pivot — provável renomeação "
            f"parcial do anexo 2.9.\ncolunas afetadas: {cols}\n"
            f"anos afetados: {sorted(nan_por_ano.index)}")
    piv["emissao_liq_mi"] = piv["emissoes_mi"] + piv["resgates_mi"]  # resgates < 0
    return piv.reset_index()


def detentores_anuais() -> pd.DataFrame:
    """Estoque da DPMFi por detentor no dezembro de cada ano (R$ bi e participação)."""
    det = ler_parquet("rmd_detentores")
    _exigir_colunas(det, ["detentor", "data", "valor_bi", "participacao"],
                    "rmd_detentores.parquet")
    det = det[det.detentor != "Total"].copy()
    dez = det[det.data.dt.month == 12].copy()
    dez["ano"] = dez.data.dt.year
    _exigir_cobertura_anual(dez, COBERTURA_DETENTORES, "detentores_anuais")
    return dez[["ano", "data", "detentor", "valor_bi", "participacao"]].reset_index(drop=True)


def detentores_mes() -> pd.DataFrame:
    det = ler_parquet("rmd_detentores")
    _exigir_colunas(det, ["detentor", "data", "valor_bi", "participacao"],
                    "rmd_detentores.parquet")
    return det[det.detentor != "Total"].copy()


def juros_por_detentor(ano: int | None = None) -> pd.DataFrame:
    """Estimativa do fluxo de juros por detentor = participação × juros nominais.

    Premissa: participação do estoque em dezembro aproxima a participação média
    do ano no dispêndio com juros (proxy — não é dado oficial por detentor).

    O `merge` é interno: anos sem linha de dezembro em `detentores` ficam de
    fora — os anos antes da cobertura do RMD 2.7 (até 2006) e o ano corrente,
    enquanto o anexo não fecha o ano. Qualquer outro ano descartado é erro.
    """
    j = juros_anuais()
    if ano is not None:
        j = j[j.ano == ano]
    det = detentores_anuais()
    # o merge interno descarta anos silenciosamente — medir antes de cruzar
    sem_match = sorted(set(j.ano) - set(det.ano))
    inesperados = [a for a in sem_match
                   if a >= COBERTURA_DETENTORES and a < date.today().year]
    if inesperados:
        raise ValueError(
            f"juros_por_detentor: anos sem dezembro em detentores: "
            f"{inesperados} — o merge interno os descartaria em silêncio")
    det = det.merge(j[["ano", "juros_mi"]], on="ano")
    det["juros_estimado_mi"] = det.participacao * det["juros_mi"]
    det["juros_estimado_bi"] = det.juros_estimado_mi / 1000
    return det


# ----------------------------------------------------------------- macro/mensal


def macro_mensal() -> pd.DataFrame:
    """Selic meta, IPCA 12m, IBC-Br var. 12m, desemprego e Focus 12m (mês a mês)."""
    sgs = ler_parquet("sgs")

    def _ult_do_mes(nome: str) -> pd.Series:
        s = _sgs_serie(sgs, nome).set_index("data")["valor"]
        return s.resample("ME").last()

    selic_meta = _ult_do_mes("meta_selic_copom")
    ipca12 = _ult_do_mes("ipca_12m")
    ibc = _ult_do_mes("ibcbr_dessaz")
    ibc12 = (ibc / ibc.shift(12) - 1) * 100
    selic_mensal = _ult_do_mes("selic_mensal_anualizada")

    des = ler_parquet("desemprego")
    _exigir_colunas(des, ["data", "taxa_pct"], "desemprego.parquet")
    des = des.set_index("data")["taxa_pct"]

    foc = ler_parquet("focus_inflacao12m")
    _exigir_colunas(foc, ["data_pesquisa", "suavizada", "media"],
                    "focus_inflacao12m.parquet")
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
    """Juro real ex-post e ex-ante, em duas convenções lado a lado.

    Convenção principal (colunas sem sufixo) = subtração simples
    ("Selic − IPCA 12m" e "Selic − Focus"): a régua de mercado e a das
    alegações verificadas (Kanczuk, Febraban, ANBIMA) — é a aproximação
    de 1ª ordem de Fisher, com erro i·π/(1+π): superestima o juro real em
    ~0,3 p.p. na média, até ~1,5 p.p. nos picos.

    Colunas exatas, para médias e comparações:
    - `*_fisher` … r = (1+i)/(1+π)−1 (fórmula de Fisher);
    - `juro_real_ex_post_12m` … Selic ACUMULADA em 12 meses contra o
      IPCA 12m — mesmo horizonte (o ex-post padrão compara a taxa do mês
      anualizada com a inflação de 12 meses; a diferença cresce em anos de
      virada de ciclo, ~1,8 p.p. em 2025).

    No ex-ante os horizontes já coincidem (Selic vigente a.a. × Focus 12m).
    """
    m = macro_mensal()
    i, pi, e = m["selic_mensal"], m["ipca_12m"], m["focus_ipca_12m"]
    m["juro_real_ex_post"] = i - pi
    m["juro_real_ex_ante"] = i - e
    m["juro_real_ex_post_fisher"] = ((1 + i / 100) / (1 + pi / 100) - 1) * 100
    m["juro_real_ex_ante_fisher"] = ((1 + i / 100) / (1 + e / 100) - 1) * 100
    mensal = (1 + i / 100) ** (1 / 12) - 1  # taxa do mês (anualizada -> mensal)
    acum12 = ((1 + mensal).rolling(12)
               .apply(lambda x: x.prod(), raw=True) - 1) * 100
    m["juro_real_ex_post_12m"] = acum12 - pi
    return m


def focus_anuais() -> pd.DataFrame:
    d = ler_parquet("focus_anuais")
    _exigir_colunas(d, ["indicador", "data_pesquisa", "data_referencia", "media"],
                    "focus_anuais.parquet")
    return d


def crescimento_pib_real() -> pd.Series:
    """Variação anual do PIB real (volume) — IBGE SIDRA, fbcf.parquet.

    Crescimento do ano = média anual do índice de volume do PIB a preços de
    mercado sobre a média do ano anterior (a variação "do ano" do IBGE).
    É o g oficial da comparação r > g: deflacionar o PIB nominal pelo
    IPCA 12m é aproximação com erro de ~1 p.p. na média, até ~5 p.p. em
    anos de choque de preços (2021: 10,1 vs 4,8).
    """
    f = ler_parquet("fbcf")
    _exigir_colunas(f, ["setor", "data", "indice"], "fbcf.parquet")
    pib = f[f.setor == "PIB a preços de mercado"]
    if pib.empty:
        raise ValueError(
            "crescimento_pib_real: setor 'PIB a preços de mercado' ausente em "
            f"fbcf.parquet — setores: {sorted(f.setor.unique())}")
    s = pib.set_index("data")["indice"]
    if s.index.year.min() > ANO_INICIO:
        raise ValueError(
            f"crescimento_pib_real: cobertura recuou — começa em "
            f"{s.index.min():%Y-%m} (esperado desde {ANO_INICIO})")
    anual = s.groupby(s.index.year).mean()
    return anual.pct_change() * 100


# ------------------------------------------------------------------ custo médio


def custo_medio() -> pd.DataFrame:
    c = ler_parquet("rmd_custo_medio")
    _exigir_colunas(c, ["data", "escopo", "tabela", "taxa_pct_aa"],
                    "rmd_custo_medio.parquet")
    return c


# cobertura mínima por tabela do RMD 4.x (a série "12m" precisa de 12 meses
# de histórico, então começa um ano depois da mensal)
COBERTURA_CUSTO = {"estoque mensal": "2005-01", "estoque 12m": "2005-12"}


def custo_medio_dpf(tabela: str = "estoque mensal") -> pd.DataFrame:
    """Custo médio do estoque (% a.a.), escopo DPF.

    `tabela` = "estoque mensal" (taxa anualizada do mês) ou "estoque 12m"
    (acumulada em 12 meses — a janela coerente para comparar com o
    crescimento ANUAL do PIB no i−g; o `documentos.py` usa 12m).
    """
    c = ler_parquet("rmd_custo_medio")
    _exigir_colunas(c, ["data", "escopo", "tabela", "taxa_pct_aa"],
                    "rmd_custo_medio.parquet")
    d = c[(c.tabela == tabela) & (c.escopo == "DPF")]
    if d.empty:
        raise ValueError(
            f"custo_medio_dpf: o filtro {tabela!r}/'DPF' não casou nenhuma "
            f"linha — tabelas disponíveis: {sorted(c.tabela.unique())}")
    desde = COBERTURA_CUSTO.get(tabela, "2005-01")
    if d.data.min().to_period("M") > pd.Period(desde):
        raise ValueError(
            f"custo_medio_dpf: cobertura recuou — começa em "
            f"{d.data.min():%Y-%m} (esperado desde {desde})")
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
        if ano not in set(j.ano):
            raise ValueError(
                f"validacao_bndes: o ano {ano} (Estudo BNDES) não existe em "
                f"juros_anuais — anos disponíveis: {sorted(j.ano)}")
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


# --------------------------------------------------------------- juros × primário


def juros_primario_12m() -> pd.DataFrame:
    """Juros nominais e resultado primário, acumulados 12 meses (% do PIB).

    SGS `juros_pib_12m` e `primario_pib_12m` — mesmo calendário de datas.
    """
    sgs = ler_parquet("sgs")

    def _serie(nome: str) -> pd.Series:
        return _sgs_serie(sgs, nome).set_index("data")["valor"].dropna()

    a = _serie("juros_pib_12m").rename("juros_pib_12m")
    b = _serie("primario_pib_12m").rename("primario_pib_12m")
    if not a.index.equals(b.index):
        raise ValueError(
            f"juros_primario_12m: calendários divergentes entre "
            f"juros_pib_12m ({len(a)} datas) e primario_pib_12m ({len(b)} datas)")
    return pd.concat([a, b], axis=1)
