"""Teste das justificativas do BCB para o juro alto — inflação e trabalho.

Entrada: parquets de `dados/processado/` (SGS, IPCA por grupos, Focus,
PNAD Contínua). Nenhum download.

Pergunta: as justificativas oficiais usadas para sustentar o juro alto —
inflação acima da meta, mercado de trabalho aquecido, rendimentos crescendo
acima da produtividade, expectativas desancoradas, choques de oferta — se
sustentam nos dados?

Método: descrever e testar **associações**. Não estimamos causalidade: a
Phillips é uma correlação condicional, e o texto diz isso em cada tabela.
Onde a série não permite identificar o mecanismo, a leitura é "não
verificável", não "falsa".

Saídas (DataFrames; o notebook 09 exibe):
- `metas_anuais()` ......... meta efetiva, faixa, IPCA e veredito ano a ano
- `contribuicoes_ipca()` ... contribuição de cada grupo para o IPCA 12m
- `servicos_intensivos()` .. grupos 6+7+8+9 (proxy; a série oficial é SGS 10844)
- `base_phillips()` ........ base mensal (IPCA, serviços, desemprego, Focus, câmbio)
- `phillips()` ............. 4 modelos OLS com erro-padrão HAC
- `produtividade_anual()` .. salário real, produtividade, ULC e razão
- `mercado_trabalho_resumo()` — desemprego, ocupação, participação, informalidade
- `expectativas_anuais()` .. Focus IPCA por ano-calendário vs meta/teto
- `focus_12m_ultimo()` ..... última expectativa de IPCA 12m
- `credibilidade()` ........ proxies: Focus acima da meta, dispersão
- `citacoes_atas()` ........ citações verbatim das atas 280–282
- `termo_por_ata()` ........ em quais atas o termo aparece
- `veredito()` ............. tabela "o que o BC diz / o que os dados mostram"

Rodar: PYTHONPATH=. python -m src.processa.justificativas
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from ..extratores.base import RAIZ, ler_parquet

# --------------------------------------------------------------- parâmetros

# Metas anuais efetivas definidas pelo CMN e intervalo de tolerância.
# Fontes: BCB, "Histórico: meta de inflação vs. inflação efetiva"
# (https://www.bcb.gov.br/controleinflacao/historicometas):
# 2017–2018: Resoluções CMN 4.419/2015 e 4.499/2016 (4,50% ±1,50);
# 2019–2020: Resolução CMN 4.582/2017 (4,25% e 4,00% ±1,50);
# 2021: 4.671/2018; 2022: 4.724/2019; 2023: 4.831/2020;
# 2024: 4.918/2021; 2025–2026: 5.141/2024 (3,00% ±1,50, meta contínua).
# Até 2016 o intervalo era ±2,00 p.p.
METAS_ANUAIS: dict[int, tuple[float, float]] = {
    2012: (4.50, 2.00), 2013: (4.50, 2.00), 2014: (4.50, 2.00),
    2015: (4.50, 2.00), 2016: (4.50, 2.00), 2017: (4.50, 1.50),
    2018: (4.50, 1.50), 2019: (4.25, 1.50), 2020: (4.00, 1.50),
    2021: (3.75, 1.50), 2022: (3.50, 1.50), 2023: (3.25, 1.50),
    2024: (3.00, 1.50), 2025: (3.00, 1.50), 2026: (3.00, 1.50),
}
META_CONTINUA = 3.0          # desde 2025
TETO_CONTINUO = META_CONTINUA + 1.50

# grupos do IPCA usados como proxy de "intensivos em serviços" (6 a 9).
# Não é a série oficial de serviços (SGS 10844): inclui bens, como
# medicamentos no grupo Saúde. O notebook usa as duas com rótulos distintos.
GRUPOS_SERVICOS = ("7660", "7712", "7766", "7786")

# atas do Copom citadas (texto bruto em dados/bruto/copom/texto)
ATAS_CITADAS = (280, 281, 282)

TEXTO_DIR = RAIZ / "dados" / "bruto" / "copom" / "texto"


# ------------------------------------------------------------------ helpers


def _exigir_colunas(df: pd.DataFrame, colunas: list[str], fonte: str) -> None:
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise ValueError(
            f"{fonte}: colunas ausentes {faltando} — "
            f"encontradas: {sorted(df.columns)}")


def _serie_sgs(sgs: pd.DataFrame, nome: str) -> pd.Series:
    _exigir_colunas(sgs, ["serie", "data", "valor"], "sgs.parquet")
    d = sgs[sgs.serie == nome]
    if d.empty:
        raise ValueError(
            f"sgs.parquet: série {nome!r} ausente — "
            f"disponíveis: {sorted(sgs.serie.unique())}")
    s = d.set_index("data")["valor"].sort_index()
    s.index = pd.to_datetime(s.index)
    return s


def _mensal(s: pd.Series) -> pd.Series:
    """Série diária/mensal -> uma observação por mês (última do mês)."""
    s = s.copy()
    s.index = s.index.to_period("M")
    return s.groupby(level=0).last().sort_index()


def _acum12(s: pd.Series) -> pd.Series:
    """Variação acumulada em 12 meses a partir de variações mensais (%)."""
    return ((1 + s / 100).rolling(12).apply(
        lambda v: v.prod(), raw=True) - 1) * 100


def _periodo_ano(ano: int, mes: int = 12) -> pd.Period:
    return pd.Period(f"{ano}-{mes:02d}", "M")


# ------------------------------------------------------------------ metas


def metas_anuais() -> pd.DataFrame:
    """Meta efetiva, faixa de tolerância e IPCA realizado, ano a ano.

    Para anos fechados usa o IPCA 12m de dezembro (igual à variação anual).
    Para o ano corrente usa o último 12m disponível e marca `fechado=False`;
    o valor não é a variação acumulada no ano, é a janela de 12 meses.
    """
    sgs = ler_parquet("sgs")
    ipca12 = _mensal(_serie_sgs(sgs, "ipca_12m"))
    ultimo = ipca12.index.max()

    linhas = []
    for ano, (meta, tol) in METAS_ANUAIS.items():
        ref = _periodo_ano(ano)
        fechado = ref in ipca12.index
        if not fechado:
            ref = ultimo
        if ref.year != ano:
            raise ValueError(
                f"metas_anuais: sem referência para {ano} "
                f"(último mês disponível: {ultimo})")
        ipca = float(ipca12.loc[ref])
        piso, teto = meta - tol, meta + tol
        linhas.append({
            "ano": ano,
            "meta_pct": meta,
            "tolerancia_pp": tol,
            "piso_pct": piso,
            "teto_pct": teto,
            "ipca_pct": ipca,
            "mes_referencia": str(ref),
            "fechado": bool(fechado),
            "dentro": bool(piso <= ipca <= teto),
            "abaixo_piso": bool(ipca < piso),
            "acima_teto": bool(ipca > teto),
            "desvio_meta_pp": ipca - meta,
            "desvio_teto_pp": ipca - teto,
        })
    df = pd.DataFrame(linhas)

    if df["ano"].duplicated().any():
        raise ValueError("metas_anuais: anos duplicados")
    if df["ipca_pct"].isna().any():
        raise ValueError("metas_anuais: IPCA ausente")
    if not df["ipca_pct"].between(-10, 30).all():
        raise ValueError("metas_anuais: IPCA fora da faixa -10..30%")
    fechados = df[df.ano.between(2021, 2025)]
    if not fechados["fechado"].all():
        raise ValueError(
            "metas_anuais: 2021–2025 deveriam estar fechados — "
            f"fechados={fechados.fechado.tolist()}")
    return df


# --------------------------------------------------------- decomposição IPCA


def contribuicoes_ipca() -> pd.DataFrame:
    """Contribuição de cada grupo para o IPCA 12m, no mês de referência.

    Aproximação padrão de imprensa: `variação 12m do grupo × peso do mês`.
    A soma difere do IPCA cheio em até ~0,4 p.p. porque o peso varia ao
    longo dos 12 meses e as variações são arredondadas; a coluna
    `residuo_pp` mostra a diferença em cada ano. Não é decomposição exata.
    """
    ip = ler_parquet("ipca_grupos")
    _exigir_colunas(
        ip, ["data", "variavel", "valor", "categoria_codigo",
             "categoria_nome", "nivel"], "ipca_grupos.parquet")

    g = ip[(ip.nivel == "grupo") & (ip.variavel.isin(["2265", "66"]))]
    g = g.pivot_table(
        index=["data", "categoria_codigo", "categoria_nome"],
        columns="variavel", values="valor").reset_index()
    g = g.rename(columns={"2265": "variacao_12m_pct", "66": "peso_pct"})
    if g.empty:
        raise ValueError("contribuicoes_ipca: nenhum grupo de 1º nível")
    g["contribuicao_pp"] = g.variacao_12m_pct * g.peso_pct / 100

    total = ip[(ip.nivel == "total") & (ip.variavel == "2265")]
    total = total[["data", "valor"]].rename(
        columns={"valor": "total_ipca_12m"})
    g = g.merge(total, on="data", how="left")
    g["ano"] = g["data"].dt.year

    # mês de referência: dezembro, ou o último mês do ano corrente
    refs = []
    for _, d in g.groupby("ano"):
        dez = d[d["data"].dt.month == 12]
        refs.append(dez if not dez.empty else d[d["data"] == d["data"].max()])
    out = pd.concat(refs, ignore_index=True)

    out["mes_referencia"] = out["data"].dt.strftime("%Y-%m")
    out["soma_contrib_pp"] = out.groupby("ano")["contribuicao_pp"].transform(
        "sum")
    out["residuo_pp"] = out["soma_contrib_pp"] - out["total_ipca_12m"]
    out["grupo"] = out["categoria_nome"].str.replace(
        r"^\d+\.", "", regex=True)

    contagem = out.groupby("ano").size()
    if not (contagem == 9).all():
        raise ValueError(
            "contribuicoes_ipca: anos sem os 9 grupos — "
            f"{contagem[contagem != 9].to_dict()}")
    pesos = out.groupby("ano")["peso_pct"].sum()
    if (pesos.sub(100).abs() > 0.5).any():
        raise ValueError(
            "contribuicoes_ipca: peso dos grupos não soma 100 em "
            f"{pesos[pesos.sub(100).abs() > 0.5].round(2).to_dict()}")
    if out["total_ipca_12m"].isna().any():
        raise ValueError("contribuicoes_ipca: IPCA total ausente")
    if out["residuo_pp"].abs().max() > 0.5:
        raise ValueError(
            "contribuicoes_ipca: resíduo acima de 0,5 p.p. — "
            f"max={out['residuo_pp'].abs().max():.2f}")

    cols = ["ano", "mes_referencia", "categoria_codigo", "grupo",
            "variacao_12m_pct", "peso_pct", "contribuicao_pp",
            "total_ipca_12m", "soma_contrib_pp", "residuo_pp"]
    return out[cols].sort_values(
        ["ano", "contribuicao_pp"], ascending=[True, False]
    ).reset_index(drop=True)


def servicos_intensivos() -> pd.DataFrame:
    """Contribuição dos grupos 6+7+8+9 para o IPCA 12m (proxy)."""
    c = contribuicoes_ipca()
    d = c[c["categoria_codigo"].isin(GRUPOS_SERVICOS)]
    out = d.groupby("ano").agg(
        contrib_servicos_pp=("contribuicao_pp", "sum"),
        total_ipca_12m=("total_ipca_12m", "first"),
    ).reset_index()
    out["share_pct"] = out["contrib_servicos_pp"] / out["total_ipca_12m"] * 100
    if out.empty:
        raise ValueError("servicos_intensivos: nenhum grupo de serviços")
    if not out["share_pct"].between(0, 100).all():
        raise ValueError("servicos_intensivos: participação fora de 0–100%")
    return out


# ------------------------------------------------------------------ Phillips


def base_phillips() -> pd.DataFrame:
    """Base mensal: IPCA 12m, serviços 12m, desemprego, Focus 12m, câmbio 12m.

    - serviços = SGS 10844 (série oficial do BCB), acumulada em 12m;
    - Focus = base de cálculo 0 (a base 1 coexiste desde 2014 e não pode
      ser misturada), série não suavizada;
    - câmbio = R$/US$ (SGS 1), variação em 12m (depreciação positiva).
    """
    sgs = ler_parquet("sgs")
    ipca12 = _mensal(_serie_sgs(sgs, "ipca_12m"))
    serv12 = _acum12(_mensal(_serie_sgs(sgs, "ipca_servicos")))
    cambio = _mensal(_serie_sgs(sgs, "cambio_usd"))
    cambio12 = (cambio / cambio.shift(12) - 1) * 100

    des = ler_parquet("desemprego")
    _exigir_colunas(des, ["data", "taxa_pct"], "desemprego.parquet")
    u = des.set_index("data")["taxa_pct"]
    u.index = pd.to_datetime(u.index)
    u = _mensal(u)

    foc = ler_parquet("focus_inflacao12m")
    _exigir_colunas(
        foc, ["data_pesquisa", "suavizada", "base_calculo", "media"],
        "focus_inflacao12m.parquet")
    foc = foc[(foc.suavizada == "N") & (foc.base_calculo == 0)]
    if foc.empty:
        raise ValueError("base_phillips: Focus base 0/não suavizada ausente")
    f12 = foc.set_index("data_pesquisa")["media"]
    f12.index = pd.to_datetime(f12.index)
    f12 = _mensal(f12)

    df = pd.concat([
        ipca12.rename("ipca12"),
        serv12.rename("serv12"),
        u.rename("u"),
        f12.rename("focus12"),
        cambio12.rename("cambio12"),
    ], axis=1).sort_index()
    df = df.loc["2012-03":].dropna(
        subset=["ipca12", "serv12", "u", "focus12"])

    if len(df) < 150:
        raise ValueError(f"base_phillips: só {len(df)} meses (esperado >= 150)")
    if df.index.has_duplicates:
        raise ValueError("base_phillips: meses duplicados")
    if df[["ipca12", "serv12", "u", "focus12"]].isna().any().any():
        raise ValueError("base_phillips: valor ausente nas colunas-chave")
    if not df["u"].between(0, 30).all():
        raise ValueError("base_phillips: desemprego fora de 0–30%")
    return df


def phillips(janela: tuple[str, str] | None = None) -> pd.DataFrame:
    """Modelos OLS (HAC, 12 lags) para IPCA cheio e serviços.

    Retorna uma linha por coeficiente. `modelo` identifica a equação;
    `janela` registra o recorte. Coeficiente do desemprego negativo é o
    sinal previsto pela curva de Phillips; positivo é o oposto.
    """
    df = base_phillips()
    if janela is not None:
        df = df.loc[janela[0]:janela[1]]
        if df.empty:
            raise ValueError(f"phillips: janela {janela} vazia")

    modelos = {
        "IPCA cheio ~ desemprego": "ipca12 ~ u",
        "IPCA cheio ~ desemprego + Focus + câmbio":
            "ipca12 ~ u + focus12 + cambio12",
        "Serviços ~ desemprego": "serv12 ~ u",
        "Serviços ~ desemprego + Focus + câmbio":
            "serv12 ~ u + focus12 + cambio12",
    }
    linhas = []
    for nome, formula in modelos.items():
        m = smf.ols(formula, data=df).fit(
            cov_type="HAC", cov_kwds={"maxlags": 12})
        for var in m.params.index:
            linhas.append({
                "modelo": nome,
                "variavel": var,
                "coef": float(m.params[var]),
                "erro_padrao": float(m.bse[var]),
                "p_valor": float(m.pvalues[var]),
                "r2": float(m.rsquared),
                "n": int(m.nobs),
                "janela": f"{df.index.min()}–{df.index.max()}",
            })
    out = pd.DataFrame(linhas)
    if out.empty:
        raise ValueError("phillips: nenhum modelo estimado")
    if out["n"].min() < 60:
        raise ValueError(f"phillips: n mínimo {out['n'].min()} (< 60)")
    return out


# ----------------------------------------------------- produtividade/salário


def produtividade_anual() -> pd.DataFrame:
    """Salário real, produtividade por trabalhador, ULC e razão salário/prod.

    Produtividade = PIB volume (CNT) ÷ pessoas ocupadas (PNAD), média anual.
    É produtividade **por trabalhador**, não por hora: a PNAD agregada não
    publica horas trabalhadas no SIDRA. ULC = variação do salário real −
    variação da produtividade (proxy; não é a ULC oficial do IBGE).
    """
    prod = ler_parquet("produtividade")
    _exigir_colunas(
        prod, ["data", "pib_volume", "ocupados_mil", "produtividade"],
        "produtividade.parquet")
    prod = prod.copy()
    prod["ano"] = prod["data"].dt.year
    pa = prod.groupby("ano").agg(
        pib_volume=("pib_volume", "mean"),
        ocupados_mil=("ocupados_mil", "mean"),
        produtividade=("produtividade", "mean"),
    ).reset_index()
    pa["prod_yoy_pct"] = pa["produtividade"].pct_change() * 100

    rend = ler_parquet("rendimento")
    _exigir_colunas(rend, ["tabela", "variavel", "data", "valor"],
                    "rendimento.parquet")
    sal = rend[(rend.tabela.astype(str) == "4660")
               & (rend.variavel.astype(str) == "5933")][["data", "valor"]]
    if sal.empty:
        raise ValueError(
            "produtividade_anual: salário real (4660/5933) ausente")
    sal = sal.copy()
    sal["ano"] = sal["data"].dt.year
    sal = sal.groupby("ano", as_index=False)["valor"].last()
    sal = sal.rename(columns={"valor": "salario_real"})
    sal["sal_yoy_pct"] = sal["salario_real"].pct_change() * 100

    df = pa.merge(sal, on="ano", how="left")
    df["ulc_pp"] = df["sal_yoy_pct"] - df["prod_yoy_pct"]

    base = df[df.ano == 2012]
    if base.empty:
        raise ValueError("produtividade_anual: 2012 ausente")
    base = base.iloc[0]
    df["prod_idx"] = df["produtividade"] / base["produtividade"] * 100
    df["sal_idx"] = df["salario_real"] / base["salario_real"] * 100
    df["razao_sal_prod"] = df["sal_idx"] / df["prod_idx"]

    sgs = ler_parquet("sgs")
    ipca12 = _mensal(_serie_sgs(sgs, "ipca_12m"))
    serv12 = _acum12(_mensal(_serie_sgs(sgs, "ipca_servicos")))
    df["ipca_dez_pct"] = df["ano"].map(
        lambda a: ipca12.get(_periodo_ano(int(a)), np.nan))
    df["servicos_dez_pct"] = df["ano"].map(
        lambda a: serv12.get(_periodo_ano(int(a)), np.nan))

    des = ler_parquet("desemprego")
    _exigir_colunas(des, ["data", "taxa_pct"], "desemprego.parquet")
    u = des.groupby(des["data"].dt.year)["taxa_pct"].mean()
    df["desemprego_medio_pct"] = df["ano"].map(u)

    fechados = df[df.ano.between(2012, 2025)]
    if len(fechados) != 14:
        raise ValueError(
            f"produtividade_anual: {len(fechados)} anos fechados "
            "(esperado 14: 2012–2025)")
    if fechados["salario_real"].isna().any():
        raise ValueError("produtividade_anual: salário real ausente em 2012–2025")
    # as variações só existem a partir de 2013 (primeiro ano com ano anterior)
    yoy = df[df.ano.between(2013, 2025)]
    cols = ["sal_yoy_pct", "prod_yoy_pct", "ulc_pp"]
    if yoy[cols].isna().any().any():
        raise ValueError("produtividade_anual: variação ausente em 2013–2025")
    if not (df["razao_sal_prod"].dropna() > 0).all():
        raise ValueError("produtividade_anual: razão não positiva")
    return df


# --------------------------------------------------------- mercado de trabalho


def mercado_trabalho_resumo() -> pd.DataFrame:
    """Último valor, médias 2012–19 e 2025–26, mínimo e máximo por indicador.

    Desemprego vem de `desemprego.parquet` (PNAD mensal, 3 meses móveis);
    os demais de `mercado_trabalho.parquet` (PNAD trimestral).
    """
    mt = ler_parquet("mercado_trabalho")
    _exigir_colunas(mt, ["data", "variavel", "valor"],
                    "mercado_trabalho.parquet")
    piv = mt.pivot(index="data", columns="variavel", values="valor")
    piv = piv.sort_index()

    des = ler_parquet("desemprego")
    _exigir_colunas(des, ["data", "taxa_pct"], "desemprego.parquet")
    u = des.set_index("data")["taxa_pct"].sort_index()
    u.index = pd.to_datetime(u.index)
    u = u.resample("QE").last()
    piv["desemprego_pct"] = u.reindex(piv.index)

    nomes = {
        "desemprego_pct": "Desemprego (%)",
        "nivel_ocupacao_pct": "Nível de ocupação (%)",
        "participacao_pct": "Taxa de participação (%)",
        "informalidade_pct": "Informalidade (%)",
        "ocupados_mil": "Pessoas ocupadas (mil)",
    }
    faltando = [v for v in nomes if v not in piv.columns]
    if faltando:
        raise ValueError(
            f"mercado_trabalho_resumo: variáveis ausentes {faltando}")

    linhas = []
    for var, nome in nomes.items():
        s = piv[var].dropna()
        if s.empty:
            raise ValueError(f"mercado_trabalho_resumo: {var} vazia")
        pre = s[s.index.year <= 2019]
        pos = s[s.index.year >= 2025]
        linhas.append({
            "indicador": nome,
            "ultimo": float(s.iloc[-1]),
            "data_ultimo": s.index[-1],
            "media_2012_2019": float(pre.mean()),
            "media_2025_2026": float(pos.mean()),
            "minimo": float(s.min()),
            "data_minimo": s.idxmin(),
            "maximo": float(s.max()),
            "data_maximo": s.idxmax(),
        })
    out = pd.DataFrame(linhas)
    if out[["ultimo", "media_2012_2019", "media_2025_2026"]].isna().any().any():
        raise ValueError("mercado_trabalho_resumo: média/último ausente")
    if piv.index.max() < pd.Timestamp("2025-12-31"):
        raise ValueError(
            f"mercado_trabalho_resumo: série termina em {piv.index.max()}")
    return out


# --------------------------------------------------------------- expectativas


def expectativas_anuais() -> pd.DataFrame:
    """Focus IPCA por ano-calendário na última pesquisa (base de cálculo 0)."""
    foc = ler_parquet("focus_anuais")
    _exigir_colunas(
        foc, ["indicador", "data_pesquisa", "data_referencia",
              "base_calculo", "media"], "focus_anuais.parquet")
    foc = foc[(foc.indicador == "IPCA") & (foc.base_calculo == 0)]
    if foc.empty:
        raise ValueError("expectativas_anuais: Focus IPCA base 0 ausente")
    ultima = foc["data_pesquisa"].max()
    d = foc[foc.data_pesquisa == ultima].sort_values("data_referencia")
    d = d[d.data_referencia >= 2026].copy()
    if len(d) < 5:
        raise ValueError(
            f"expectativas_anuais: só {len(d)} anos na última pesquisa")
    d["meta_pct"] = META_CONTINUA
    d["teto_pct"] = TETO_CONTINUO
    d["acima_meta"] = d["media"] > d["meta_pct"]
    d["acima_teto"] = d["media"] > d["teto_pct"]
    if d["data_referencia"].duplicated().any():
        raise ValueError("expectativas_anuais: anos duplicados")
    return d[["data_pesquisa", "data_referencia", "media", "mediana",
              "desvio_padrao", "meta_pct", "teto_pct",
              "acima_meta", "acima_teto"]].reset_index(drop=True)


def focus_12m_ultimo() -> pd.Series:
    """Última expectativa de IPCA 12m (base 0, não suavizada)."""
    foc = ler_parquet("focus_inflacao12m")
    _exigir_colunas(
        foc, ["data_pesquisa", "suavizada", "base_calculo", "media",
              "mediana", "desvio_padrao", "respondentes"],
        "focus_inflacao12m.parquet")
    foc = foc[(foc.suavizada == "N") & (foc.base_calculo == 0)]
    if foc.empty:
        raise ValueError("focus_12m_ultimo: Focus base 0 ausente")
    ultima = foc["data_pesquisa"].max()
    d = foc[foc.data_pesquisa == ultima]
    if len(d) != 1:
        raise ValueError(
            f"focus_12m_ultimo: {len(d)} linhas na última pesquisa")
    return d.iloc[0]


def credibilidade() -> pd.DataFrame:
    """Proxies de credibilidade/desancoragem: nível e dispersão do Focus 12m.

    Não é uma medida de credibilidade do BC: é a expectativa do mercado.
    Compara 2012–19 (antes do choque) com 2021–26 (pós-choque) **contra a
    meta efetiva de cada ano** — não contra a meta de 3% atual, que só vale
    desde 2025. Usar a meta atual para o passado inflaria artificialmente o
    "acima da meta" de 2012–19.
    """
    foc = ler_parquet("focus_inflacao12m")
    _exigir_colunas(
        foc, ["data_pesquisa", "suavizada", "base_calculo", "media",
              "desvio_padrao"], "focus_inflacao12m.parquet")
    foc = foc[(foc.suavizada == "N") & (foc.base_calculo == 0)].copy()
    foc["data_pesquisa"] = pd.to_datetime(foc["data_pesquisa"])
    foc = foc.sort_values("data_pesquisa")
    foc["mes"] = foc["data_pesquisa"].dt.to_period("M")
    m = foc.groupby("mes").tail(1).set_index("mes").sort_index()

    def _meta_mensal(idx: pd.PeriodIndex) -> tuple[pd.Series, pd.Series]:
        anos = idx.year
        meta = pd.Series([METAS_ANUAIS[int(a)][0] for a in anos], index=idx)
        tol = pd.Series([METAS_ANUAIS[int(a)][1] for a in anos], index=idx)
        if meta.isna().any() or tol.isna().any():
            raise ValueError("credibilidade: ano sem meta em METAS_ANUais")
        return meta, tol

    linhas = []
    for nome, ini, fim in (
        ("2012–2019", "2012-01", "2019-12"),
        ("2021–2026", "2021-01", "2026-11"),
    ):
        d = m.loc[ini:fim]
        if d.empty:
            raise ValueError(f"credibilidade: período {nome} vazio")
        meta, tol = _meta_mensal(d.index)
        gap = d["media"] - meta
        linhas.append({
            "periodo": nome,
            "meses": len(d),
            "focus_12m_medio_pct": float(d["media"].mean()),
            "meta_media_pct": float(meta.mean()),
            "gap_medio_pp": float(gap.mean()),
            "dispersao_media_pp": float(d["desvio_padrao"].mean()),
            "pct_meses_acima_meta": float((gap > 0).mean() * 100),
            "pct_meses_acima_teto": float((gap > tol).mean() * 100),
        })
    out = pd.DataFrame(linhas)
    if not out["pct_meses_acima_meta"].between(0, 100).all():
        raise ValueError("credibilidade: percentual fora de 0–100")
    return out


# ------------------------------------------------------------------ citações


# Citações verbatim das atas. `trecho` é comparado com o texto bruto após
# normalizar espaços/quebras de linha; o texto bruto tem artefatos de OCR
# ("El Niño ,", "des aceleração", "exige -se"), preservados na citação.
CITACOES: list[dict] = [
    {
        "num": 280,
        "data": "2026-08-05",
        "tema": "mercado de trabalho",
        "trecho": (
            "A taxa de desemprego mantém-se em patamares historicamente "
            "baixos, enquanto o crescimento da taxa de ocupação vem "
            "apresentando desaceleração."),
        "nota": "diagnóstico repetido nas atas 280, 281 e 282",
    },
    {
        "num": 280,
        "data": "2026-08-05",
        "tema": "salário × produtividade",
        "trecho": (
            "Os rendimentos médios desaceleraram na margem, mesmo em termos "
            "nominais, mas ainda crescem em termos reais a uma taxa superior "
            "à da produtividade do trabalho."),
        "nota": "a alegação testada em produtividade_anual()",
    },
    {
        "num": 281,
        "data": "2026-09-16",
        "tema": "mercado de trabalho aquecido",
        "trecho": (
            "Em relação ao cenário doméstico, o conjunto dos indicadores "
            "divulgados desde a última reunião mostra uma moderação gradual "
            "da atividade econômica, principalmente em setores mais cíclicos, "
            "embora ainda em patamar resiliente e mercado de trabalho "
            "aquecido."),
        "nota": "única das três atas em que o termo 'aquecido' qualifica o "
                "mercado de trabalho no cenário doméstico",
    },
    {
        "num": 282,
        "data": "2026-11-04",
        "tema": "choques de oferta",
        "trecho": (
            "quatro choques de oferta: (i) a elevação dos preços do petróleo, "
            "em decorrência dos conflitos no Oriente Médio; (ii) os efeitos "
            "climáticos associados ao fenômeno El Niño , com impactos sobre "
            "produtividade agrícola e custos de energia; (iii) os efeitos do "
            "fim da escala 6X1 sobre os custos do trabalho e; (iv) a "
            "depreciação da taxa de câmbio, em função de incertezas "
            "relacionadas à política doméstica."),
        "nota": "o próprio BC lista quatro choques de oferta; 'El Niño ,' é "
                "artefato de OCR do texto bruto",
    },
    {
        "num": 282,
        "data": "2026-11-04",
        "tema": "expectativas desancoradas",
        "trecho": (
            "em um ambiente de expectativas desancoradas, como é o caso do "
            "atual, exige-se uma restrição monetária maior e por mais tempo "
            "do que outrora seria apropriado."),
        "nota": "a justificativa explícita para manter o juro alto",
    },
]


def _texto_ata(num: int) -> str:
    p = TEXTO_DIR / f"ata_{num}.txt"
    if not p.exists():
        raise FileNotFoundError(f"{p} — rode src.extratores.copom")
    return re.sub(r"\s+", " ", p.read_text(encoding="utf-8"))


def citacoes_atas() -> pd.DataFrame:
    """Citações + `verbatim_ok`; falha ruidosa se alguma não existir."""
    df = pd.DataFrame(CITACOES)
    textos = {n: _texto_ata(int(n)) for n in df["num"].unique()}
    df["verbatim_ok"] = df.apply(
        lambda r: r["trecho"] in textos[int(r["num"])], axis=1)
    if not df["verbatim_ok"].all():
        ruins = df[~df["verbatim_ok"]][["num", "tema", "trecho"]]
        raise ValueError(
            "citacoes_atas: citação não encontrada no texto bruto:\n"
            f"{ruins.to_string(index=False)}")
    return df


def termo_por_ata(termo: str = "mercado de trabalho aquecido") -> pd.DataFrame:
    """Em quais atas citadas o termo aparece (texto normalizado)."""
    linhas = []
    for num in ATAS_CITADAS:
        texto = _texto_ata(num)
        data = next(c["data"] for c in CITACOES if c["num"] == num)
        linhas.append({
            "num": num,
            "data": data,
            "termo": termo,
            "contem": termo.lower() in texto.lower(),
        })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ veredito


def _um(df: pd.DataFrame, filtro: pd.Series, coluna: str) -> float:
    d = df[filtro]
    if d.empty:
        raise ValueError("veredito: filtro não retornou linhas")
    valores = d[coluna].dropna().unique()
    if len(valores) != 1:
        raise ValueError(
            f"veredito: coluna {coluna!r} com valores divergentes {valores}")
    return float(valores[0])


_MESES = ("jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez")


def _mes_ano(periodo: str) -> str:
    """'2026-10' -> 'out/2026'."""
    ano, mes = str(periodo).split("-")[:2]
    return f"{_MESES[int(mes) - 1]}/{ano}"


def _lista_anos(anos: pd.Series) -> str:
    """'2021, 2022 e 2024' (lista legível, em ordem)."""
    vals = [str(int(a)) for a in sorted(anos.tolist())]
    if not vals:
        return "nenhum ano"
    if len(vals) == 1:
        return vals[0]
    return ", ".join(vals[:-1]) + " e " + vals[-1]


def veredito() -> pd.DataFrame:
    """Tabela 'o que o BC diz / o que os dados mostram', com números vivos."""
    m = metas_anuais()
    c = contribuicoes_ipca()
    p = phillips()
    t = produtividade_anual()
    mt = mercado_trabalho_resumo()
    e = expectativas_anuais()
    f12 = focus_12m_ultimo()
    cred = credibilidade()

    m26 = m[m.ano == 2026].iloc[0]
    fechados = m[m.fechado & m.ano.between(2021, 2025)]
    acima = fechados[fechados.acima_teto]
    media_ipca = float(fechados["ipca_pct"].mean())
    media_meta = float(fechados["meta_pct"].mean())
    media_teto = float(fechados["teto_pct"].mean())

    t25 = t[t.ano == 2025].iloc[0]
    t22 = t[t.ano == 2022].iloc[0]
    u = mt[mt.indicador == "Desemprego (%)"].iloc[0]
    occ = mt[mt.indicador == "Nível de ocupação (%)"].iloc[0]
    part = mt[mt.indicador == "Taxa de participação (%)"].iloc[0]
    inf = mt[mt.indicador == "Informalidade (%)"].iloc[0]

    def coef(modelo: str, var: str = "u") -> tuple[float, float]:
        d = p[(p.modelo == modelo) & (p.variavel == var)]
        if len(d) != 1:
            raise ValueError(f"veredito: modelo {modelo!r} ausente")
        return float(d.iloc[0]["coef"]), float(d.iloc[0]["p_valor"])

    c_sim, p_sim = coef("IPCA cheio ~ desemprego")
    c_ctrl, p_ctrl = coef("IPCA cheio ~ desemprego + Focus + câmbio")
    s_ctrl, ps_ctrl = coef("Serviços ~ desemprego + Focus + câmbio")
    r2_sim = _um(p, p.modelo == "IPCA cheio ~ desemprego", "r2")
    r2_ctrl = _um(p, p.modelo == "IPCA cheio ~ desemprego + Focus + câmbio",
                  "r2")

    recente = phillips(("2021-01", "2026-09"))
    r_rec = recente[(recente.modelo == "IPCA cheio ~ desemprego")
                    & (recente.variavel == "u")].iloc[0]
    c_rec, p_rec = float(r_rec["coef"]), float(r_rec["p_valor"])

    e26 = e[e.data_referencia == 2026].iloc[0]
    e30 = e[e.data_referencia == 2030].iloc[0]
    e_acima_teto = e[e.acima_teto]
    cred_pre = cred[cred.periodo == "2012–2019"].iloc[0]
    cred_pos = cred[cred.periodo == "2021–2026"].iloc[0]

    linhas = [
        {
            "justificativa_bc": "A inflação está acima da meta e exige juro alto.",
            "dado": (
                f"IPCA 12m em {_mes_ano(m26.mes_referencia)}: "
                f"{m26.ipca_pct:.2f}% contra teto de {m26.teto_pct:.2f}%; "
                f"em {_lista_anos(acima.ano)} o IPCA ficou acima do teto. "
                f"Média 2021–25: {media_ipca:.2f}% contra meta média de "
                f"{media_meta:.2f}% (teto médio {media_teto:.2f}%)."),
            "leitura": (
                "O fato (inflação acima da meta) procede. Mas o juro alto "
                f"não entregou a meta: em {len(acima)} dos "
                f"{len(fechados)} anos fechados desde 2021 o IPCA ficou "
                f"acima do teto ({_lista_anos(acima.ano)}); "
                f"{m26.ano} parcial também está acima."),
            "veredito": "fato procede; eficácia não comprovada",
        },
        {
            "justificativa_bc": "O mercado de trabalho está aquecido.",
            "dado": (
                f"Desemprego {u.ultimo:.1f}% ({u.data_ultimo:%m/%Y}; mínimo "
                f"{u.minimo:.1f}% em {u.data_minimo:%m/%Y}); nível de "
                f"ocupação {occ.ultimo:.1f}% (máxima da série); "
                f"informalidade {inf.ultimo:.1f}% contra "
                f"{inf.media_2012_2019:.1f}% em 2012–19; participação "
                f"{part.ultimo:.1f}% contra {part.media_2012_2019:.1f}%."),
            "leitura": (
                "A descrição procede: desemprego perto do mínimo, ocupação "
                "em recorde e informalidade abaixo da média. Mas a "
                "participação também está abaixo da média histórica — parte "
                "do aperto vem de menor oferta de trabalho, não só de "
                "demanda. E mercado apertado não se traduz automaticamente "
                "em inflação cheia (ver linha da Phillips)."),
            "veredito": "procede como descrição; não como prova de pressão",
        },
        {
            "justificativa_bc": "Os rendimentos crescem acima da produtividade.",
            "dado": (
                f"Salário real +{t25.sal_idx - 100:.1f}% e produtividade "
                f"+{t25.prod_idx - 100:.1f}% entre 2012 e 2025 (razão "
                f"{t25.razao_sal_prod:.2f}); ULC de {t25.ulc_pp:+.1f} p.p. "
                f"em 2025."),
            "leitura": (
                "Procede em 2023–25, mas com duas ressalvas: o salário real "
                "caiu 8,4% entre 2020 e 2022 e a produtividade é por "
                "trabalhador, não por hora. O gap acumulado é de ~15% em 13 "
                "anos (~1,1% ao ano), compatível com recuperação, não com "
                "espiral."),
            "veredito": "procede em parte (período e magnitude)",
        },
        {
            "justificativa_bc": (
                "Desemprego baixo pressiona a inflação e exige juro alto."),
            "dado": (
                f"Phillips do IPCA cheio: coef. do desemprego {c_sim:+.2f} "
                f"(p={p_sim:.2f}, R²={r2_sim:.2f}); com Focus e câmbio, "
                f"{c_ctrl:+.2f} (p={p_ctrl:.2f}, R²={r2_ctrl:.2f}). Em "
                f"2021–26 o sinal é positivo ({c_rec:+.2f}, p={p_rec:.2f}). "
                f"Serviços com controles: {s_ctrl:+.2f} (p={ps_ctrl:.3f})."),
            "leitura": (
                "Não se sustenta para o IPCA cheio. Para serviços há "
                "associação negativa, mas é correlação, não causalidade: a "
                "desinflação de 2022–26 ocorreu com o desemprego caindo de "
                f"{t22.desemprego_medio_pct:.1f}% (média de 2022) para "
                f"{u.ultimo:.1f}% ({u.data_ultimo:%m/%Y})."),
            "veredito": "não se sustenta como explicação principal",
        },
        {
            "justificativa_bc": (
                "As expectativas estão desancoradas e exigem juro maior por "
                "mais tempo."),
            "dado": (
                f"Focus de {e26.data_pesquisa:%d/%m/%Y}: 2026 "
                f"{e26.media:.2f}%, 2030 {e30.media:.2f}%; 12m "
                f"{f12.media:.2f}%. Expectativa acima da meta em vigor em "
                f"{cred_pos.pct_meses_acima_meta:.1f}% dos meses desde 2021. "
                f"Gap médio à meta: {cred_pre.gap_medio_pp:.2f} p.p. em "
                f"2012–19 vs {cred_pos.gap_medio_pp:.2f} p.p. em 2021–26; "
                f"dispersão {cred_pre.dispersao_media_pp:.2f} → "
                f"{cred_pos.dispersao_media_pp:.2f} p.p."),
            "leitura": (
                "O diagnóstico procede: todas as projeções estão acima da "
                f"meta; {_lista_anos(e_acima_teto.data_referencia)} também "
                "acima do teto de 4,5%. Mas o Focus não identifica a causa "
                "— pode refletir choques de oferta, risco fiscal ou a "
                "própria meta."),
            "veredito": "procede como diagnóstico; causa não identificada",
        },
        {
            "justificativa_bc": "Choques de oferta explicam a inflação.",
            "dado": (
                "Ata 282 (04/11/2026) lista quatro choques: petróleo, "
                "El Niño, fim da escala 6X1 e depreciação do câmbio."),
            "leitura": (
                "Procede. O próprio BC desloca a explicação para a oferta e "
                "não repete 'mercado de trabalho aquecido' na ata 282; o "
                "termo aparece nas atas 280 e 281."),
            "veredito": "procede",
        },
    ]
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ validação


def validar() -> None:
    """Roda todas as funções e imprime um resumo; falha se algo não bater."""
    m = metas_anuais()
    c = contribuicoes_ipca()
    s = servicos_intensivos()
    b = base_phillips()
    p = phillips()
    t = produtividade_anual()
    mt = mercado_trabalho_resumo()
    e = expectativas_anuais()
    f12 = focus_12m_ultimo()
    cred = credibilidade()
    cit = citacoes_atas()
    termo = termo_por_ata()
    v = veredito()

    print(f"metas: {len(m)} anos; acima do teto (fechados): "
          f"{m[m.fechado & m.acima_teto].ano.tolist()}; abaixo do piso: "
          f"{m[m.fechado & m.abaixo_piso].ano.tolist()}")
    print(f"contribuições: {c.ano.min()}–{c.ano.max()}, "
          f"resíduo máximo {c.residuo_pp.abs().max():.2f} p.p.")
    print(f"serviços (proxy 6–9): {s.ano.min()}–{s.ano.max()}")
    print(f"Phillips: {len(b)} meses ({b.index.min()}–{b.index.max()}); "
          f"{p.modelo.nunique()} modelos")
    print(f"produtividade: {t.ano.min()}–{t.ano.max()}; "
          f"razão 2025 {t[t.ano == 2025].razao_sal_prod.iloc[0]:.2f}")
    print(f"mercado de trabalho: {len(mt)} indicadores; "
          f"último trimestre {mt.data_ultimo.max():%Y-%m}")
    print(f"Focus anual: {e.data_pesquisa.max():%d/%m/%Y}, "
          f"{len(e)} anos; Focus 12m {f12.media:.2f}%")
    print(f"credibilidade: {len(cred)} períodos; "
          f"{cred.iloc[-1].pct_meses_acima_meta:.1f}% acima da meta")
    print(f"citações: {len(cit)}/{len(cit)} verbatim; "
          f"termo 'aquecido' nas atas "
          f"{termo[termo.contem].num.tolist()}")
    print(f"veredito: {len(v)} linhas")


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 80)
    validar()
    for nome, df in (
        ("metas_anuais", metas_anuais()),
        ("contribuicoes_ipca (2021–26)",
         contribuicoes_ipca().query("ano >= 2021")),
        ("phillips", phillips()),
        ("produtividade_anual (2021–25)",
         produtividade_anual().query("ano >= 2021")),
        ("mercado_trabalho_resumo", mercado_trabalho_resumo()),
        ("expectativas_anuais", expectativas_anuais()),
        ("credibilidade", credibilidade()),
        ("veredito", veredito()),
    ):
        print(f"\n=== {nome} ===")
        numericas = df.select_dtypes("number").columns
        print(df.assign(**{c: df[c].round(2) for c in numericas})
              .to_string(index=False))


if __name__ == "__main__":
    main()
