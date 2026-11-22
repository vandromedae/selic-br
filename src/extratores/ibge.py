"""Extrator IBGE (SIDRA) — mercado de trabalho, rendimento, inflação e
produtividade.

Tabelas:
- 6381, variável 4099: taxa de desocupação (PNAD Contínua, 3 meses
  móvel), Brasil -> desemprego.parquet.
- 4660/4663/5436: rendimento médio mensal e massa de rendimento da PNAD
  Contínua (anual e trimestral, desde 2012) -> rendimento.parquet.
- 1620, classificação 11255: índice de volume trimestral do PIB e da
  Formação Bruta de Capital Fixo (Contas Nacionais Trimestrais, base
  média 1995 = 100) -> fbcf.parquet.
- 1419 (2012–2019) e 7060 (2020–hoje), classificação 315: IPCA mensal,
  acumulado em 12 meses e peso, por grupo e subgrupo -> ipca_grupos.parquet.
- 1620 (PIB volume) + 6402 (pessoas ocupadas): produtividade por pessoa
  ocupada (PIB volume / ocupados) -> produtividade.parquet. É produtividade
  por trabalhador, não por hora: a PNAD agregada não publica horas
  trabalhadas no SIDRA; o texto do notebook registra essa limitação.
- 6402, variáveis 4090/4096/4097/12466: pessoas ocupadas, participação,
  nível de ocupação e informalidade (trimestral) ->
  mercado_trabalho.parquet.

A API do SIDRA exige a classificação "Setores e subsectores" (c11255) nas
tabelas da CNT; sem ela, todos os valores vêm como ".." (não se aplica).
"""

from __future__ import annotations

import re
import time

import pandas as pd
import requests

from .base import salvar_parquet

SIDRA = "https://apisidra.ibge.gov.br/values/t/6381/n1/all/v/4099/p/all?formato=json"
_UA = {"User-Agent": "juros-e-divida/1.0"}

# SIDRA: "-", "..." e ".." (não se aplicam), "X" (confidencial) e vazio
# não são número.
_NAO_NUMERO = ("-", "...", "..", "X", None, "")

# Tabelas de rendimento da PNAD Contínua (nome curto por variável; os
# rótulos completos do SIDRA têm >200 caracteres).
TABELAS_RENDIMENTO = {"4660": "anual", "4663": "anual", "5436": "trimestral"}
ROTULOS_RENDIMENTO = {
    "5929": "rendimento médio nominal (todos os trabalhos)",
    "5933": "rendimento médio real (todos os trabalhos)",
    "5932": "rendimento médio real (trabalho principal)",
    "5934": "rendimento médio real (principal, efetivo)",
    "5935": "rendimento médio real (todos, efetivo)",
    "6288": "massa de rendimento nominal",
    "6293": "massa de rendimento real",
}

# CNT trimestral: índice de volume por setor (FBCF e PIB) — ver docstring.
SIDRA_FBCF = (
    "https://apisidra.ibge.gov.br/values/t/1620/n1/all/v/583/p/all/"
    "c11255/{categoria}?formato=json"
)
CATEGORIAS_FBCF = ("93406", "90707")  # Formação bruta de capital fixo; PIB

# IPCA por grupos e subgrupos: a tabela 1419 cobre 2012–2019 e a 7060
# cobre 2020 em diante. As duas usam a mesma classificação c315 e as mesmas
# variáveis (63 = mensal, 2265 = 12 meses, 66 = peso mensal). O código
# 7169 é o índice geral, usado como conferência; 47656 (Recreação e fumo)
# não existe em 2019 e volta como "..." — o `_valor` descarta.
TABELAS_IPCA = ("1419", "7060")
CATEGORIAS_IPCA = (
    "7169",  # índice geral
    "7170", "7445", "7486", "7558", "7625", "7660", "7712", "7766", "7786",
    "7171", "7432", "7446", "7479", "7487", "7521", "7548", "7559",
    "7604", "7615", "7620", "7626", "7661", "7683", "7697", "7713",
    "47656", "7767", "7787",
)
VARIAVEIS_IPCA = {
    "63": ("mensal", "% no mês"),
    "2265": ("12m", "% em 12 meses"),
    "66": ("peso", "% do total"),
}

# Produtividade por pessoa ocupada: PIB volume (CNT, 1995 = 100) dividido
# pelas pessoas ocupadas (PNAD Contínua, em mil). A tabela 6385/6386 tem
# lacuna em 2020Q2–2022Q1; a 6402 cobre a série inteira.
PIB_VOLUME = (
    "https://apisidra.ibge.gov.br/values/t/1620/n1/all/v/583/p/all/"
    "c11255/90707?formato=json"
)
OCUPADOS = "https://apisidra.ibge.gov.br/values/t/6402/n1/all/v/4090/p/all?formato=json"

# Mercado de trabalho (PNAD Contínua trimestral, tabela 6402): pessoas
# ocupadas, taxa de participação, nível de ocupação e informalidade. A
# informalidade só é publicada a partir de 2015Q4; as demais cobrem 2012Q1
# em diante. Formato longo -> mercado_trabalho.parquet.
MERCADO_TRABALHO = (
    "https://apisidra.ibge.gov.br/values/t/6402/n1/all/"
    "v/4090,4096,4097,12466/p/all?formato=json"
)
VARIAVEIS_TRABALHO = {
    "4090": ("ocupados_mil", "pessoas ocupadas (mil)"),
    "4096": ("participacao_pct", "taxa de participação (%)"),
    "4097": ("nivel_ocupacao_pct", "nível de ocupação (%)"),
    "12466": ("informalidade_pct", "taxa de informalidade (%)"),
}


def _get(url: str) -> list[dict]:
    for tentativa in range(4):
        try:
            r = requests.get(url, headers=_UA, timeout=120)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if tentativa == 3:
                raise
            time.sleep(2 * (tentativa + 1))
    raise RuntimeError("sidra")


def baixar() -> list[dict]:
    return _get(SIDRA)


def _valor(row: dict) -> float | None:
    v = row.get("V")
    if v in _NAO_NUMERO:
        return None
    return float(v.replace(",", "."))


def _data_trimestre(periodo: str) -> pd.Timestamp:
    """D3C de tabela trimestral = AAAA + nº do trimestre (1..4).

    Ex.: '202602' = 2º trimestre de 2026 -> fim do trimestre (30/06/2026).
    """
    ano, tri = int(periodo[:4]), int(periodo[4:])
    if tri not in (1, 2, 3, 4):
        raise ValueError(f"D3C trimestral inválido: {periodo!r}")
    mes_fim = tri * 3
    return pd.Timestamp(ano, mes_fim, 1) + pd.offsets.MonthEnd(0)


def _data_mes(periodo: str) -> pd.Timestamp:
    """D3C de tabela mensal = AAAAMM -> fim do mês."""
    if len(periodo) != 6:
        raise ValueError(f"D3C mensal inválido: {periodo!r}")
    ano, mes = int(periodo[:4]), int(periodo[4:])
    if not 1 <= mes <= 12:
        raise ValueError(f"D3C mensal inválido: {periodo!r}")
    return pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0)


def _nivel_ipca(nome: str) -> str:
    """Classifica o rótulo do SIDRA: '1.X' = grupo; '11.X' = subgrupo."""
    if nome == "Índice geral":
        return "total"
    if re.match(r"^\d\.", nome):
        return "grupo"
    if re.match(r"^\d{2}\.", nome):
        return "subgrupo"
    return "outro"


def processar() -> pd.DataFrame:
    bruto = baixar()
    cab, *linhas = bruto  # primeira linha = cabeçalho
    regs = []
    for row in linhas:
        periodo = row.get("D3C", "")
        valor = _valor(row)
        if not periodo or valor is None:
            continue
        # D3C = AAAAMM do último mês do trimestre móvel
        data = pd.Timestamp(int(periodo[:4]), int(periodo[4:]), 1) + pd.offsets.MonthEnd(0)
        regs.append({
            "data": data,
            "periodo_codigo": periodo,
            "periodo_rotulo": row.get("D3N"),
            "taxa_pct": valor,
        })
    df = pd.DataFrame(regs).sort_values("data").reset_index(drop=True)
    df["unidade"] = "% (3 meses móveis)"
    return salvar_parquet(df, "desemprego")


def processar_rendimento() -> pd.DataFrame:
    """Rendimento médio e massa (PNAD Contínua, desde 2012)."""
    regs = []
    for tabela, freq in TABELAS_RENDIMENTO.items():
        url = f"https://apisidra.ibge.gov.br/values/t/{tabela}/n1/all/v/all/p/all?formato=json"
        bruto = _get(url)
        for row in bruto[1:]:
            var = row.get("D2C", "")
            if var not in ROTULOS_RENDIMENTO:  # descarta coeficientes de variação
                continue
            valor = _valor(row)
            periodo = row.get("D3C", "")
            if valor is None or not periodo:
                continue
            if freq == "anual":
                data = pd.Timestamp(int(periodo), 12, 31)
            else:  # trimestre: D3C = AAAA + nº do trimestre
                data = _data_trimestre(periodo)
            regs.append({
                "tabela": tabela,
                "frequencia": freq,
                "variavel": var,
                "conceito": ROTULOS_RENDIMENTO[var],
                "data": data,
                "periodo_codigo": periodo,
                "periodo_rotulo": row.get("D3N"),
                "valor": valor,
                "unidade": row.get("MN", ""),
            })
    df = pd.DataFrame(regs).sort_values(
        ["frequencia", "variavel", "data"]
    ).reset_index(drop=True)
    return salvar_parquet(df, "rendimento")


def processar_fbcf() -> pd.DataFrame:
    """Índice de volume trimestral: FBCF e PIB (CNT, base média 1995 = 100)."""
    regs = []
    for categoria in CATEGORIAS_FBCF:
        bruto = _get(SIDRA_FBCF.format(categoria=categoria))
        for row in bruto[1:]:
            valor = _valor(row)
            periodo = row.get("D3C", "")
            if valor is None or not periodo:
                continue
            # D3C = AAAA + nº do trimestre -> fim do trimestre
            data = _data_trimestre(periodo)
            regs.append({
                "setor": row.get("D4N", ""),
                "data": data,
                "periodo_codigo": periodo,
                "periodo_rotulo": row.get("D3N"),
                "indice": valor,
                "unidade": row.get("MN", ""),
            })
    df = pd.DataFrame(regs).sort_values(
        ["setor", "data"]
    ).reset_index(drop=True)
    return salvar_parquet(df, "fbcf")


def processar_ipca_grupos() -> pd.DataFrame:
    """IPCA mensal, 12 meses e peso, por grupo e subgrupo (2012–hoje)."""
    cats = ",".join(CATEGORIAS_IPCA)
    regs = []
    for tabela in TABELAS_IPCA:
        for var, (conceito, unidade) in VARIAVEIS_IPCA.items():
            url = (
                f"https://apisidra.ibge.gov.br/values/t/{tabela}/n1/all/"
                f"v/{var}/p/all/c315/{cats}?formato=json"
            )
            bruto = _get(url)
            for row in bruto[1:]:
                valor = _valor(row)
                periodo = row.get("D3C", "")
                if valor is None or not periodo:
                    continue
                nome = row.get("D4N", "")
                regs.append({
                    "tabela": tabela,
                    "data": _data_mes(periodo),
                    "periodo_codigo": periodo,
                    "periodo_rotulo": row.get("D3N"),
                    "variavel": var,
                    "conceito": conceito,
                    "valor": valor,
                    "unidade": unidade,
                    "categoria_codigo": row.get("D4C"),
                    "categoria_nome": nome,
                    "nivel": _nivel_ipca(nome),
                })
    df = pd.DataFrame(regs).sort_values(
        ["data", "categoria_codigo", "variavel"]
    ).reset_index(drop=True)

    # Falha ruidosa: a série tem 170+ meses, 9 grupos, 18+ subgrupos e o
    # peso dos grupos soma 100 em todo mês. Um "..." silencioso ou uma
    # mudança de classificação não pode virar análise incompleta.
    if df.empty:
        raise ValueError("IPCA por grupos: nenhuma linha")
    dup = df.duplicated(["data", "categoria_codigo", "variavel"])
    if dup.any():
        raise ValueError(f"IPCA por grupos: {int(dup.sum())} duplicatas")
    meses = df["data"].dt.to_period("M").nunique()
    if meses < 170:
        raise ValueError(f"IPCA por grupos: só {meses} meses (esperado >= 170)")
    grupos = df.loc[df.nivel == "grupo", "categoria_codigo"].nunique()
    if grupos != 9:
        raise ValueError(f"IPCA por grupos: {grupos} grupos (esperado 9)")
    subgrupos = df.loc[df.nivel == "subgrupo", "categoria_codigo"].nunique()
    if subgrupos < 18:
        raise ValueError(
            f"IPCA por grupos: {subgrupos} subgrupos (esperado >= 18)")
    pesos = df[(df.nivel == "grupo") & (df.variavel == "66")]
    soma = pesos.groupby("data")["valor"].sum()
    if (soma.sub(100).abs() > 0.5).any():
        ruim = soma.sub(100).abs().sort_values(ascending=False).head(3)
        raise ValueError(
            "IPCA por grupos: peso dos 9 grupos não soma 100 em "
            f"{len(ruim)} meses: {ruim.round(2).to_dict()}")
    total = df[(df.nivel == "total") & (df.variavel == "2265")]["valor"]
    if total.empty or total.abs().max() > 30:
        raise ValueError(
            "IPCA por grupos: 12m do índice geral fora da faixa -30..30 "
            f"(max={total.abs().max() if not total.empty else 'vazio'})")
    return salvar_parquet(df, "ipca_grupos")


def processar_produtividade() -> pd.DataFrame:
    """Produtividade por pessoa ocupada: PIB volume / ocupados (2012–hoje)."""
    def _serie(bruto: list[dict], campo: str) -> list[dict]:
        regs = []
        for row in bruto[1:]:
            valor = _valor(row)
            periodo = row.get("D3C", "")
            if valor is None or not periodo:
                continue
            regs.append({"data": _data_trimestre(periodo), campo: valor})
        return regs

    pib = pd.DataFrame(_serie(_get(PIB_VOLUME), "pib_volume"))
    emp = pd.DataFrame(_serie(_get(OCUPADOS), "ocupados_mil"))
    df = pib.merge(emp, on="data", how="inner").sort_values("data")
    df = df.reset_index(drop=True)

    if len(df) < 55:
        raise ValueError(f"Produtividade: só {len(df)} trimestres (esperado >= 55)")
    if df["data"].duplicated().any():
        raise ValueError("Produtividade: trimestres duplicados")
    if df[["pib_volume", "ocupados_mil"]].isna().any().any():
        raise ValueError("Produtividade: valor ausente após o merge")
    if (df[["pib_volume", "ocupados_mil"]] <= 0).any().any():
        raise ValueError("Produtividade: valor não positivo")
    gaps = df["data"].diff().dropna().dt.days
    if not gaps.between(80, 100).all():
        raise ValueError(
            "Produtividade: buraco na série trimestral "
            f"(gaps de {gaps.min()} a {gaps.max()} dias)")

    df["produtividade"] = df["pib_volume"] / df["ocupados_mil"] * 1000
    df["produtividade_idx"] = (
        df["produtividade"] / df["produtividade"].iloc[0] * 100)
    df["pib_idx"] = df["pib_volume"] / df["pib_volume"].iloc[0] * 100
    df["ocupados_idx"] = df["ocupados_mil"] / df["ocupados_mil"].iloc[0] * 100
    if abs(df["produtividade_idx"].iloc[0] - 100) > 1e-9:
        raise ValueError("Produtividade: índice inicial != 100")
    return salvar_parquet(df, "produtividade")


def processar_mercado_trabalho() -> pd.DataFrame:
    """Indicadores trimestrais do mercado de trabalho (PNAD Contínua).

    Formato longo: uma linha por trimestre e variável. A taxa de
    informalidade começa em 2015Q4; as demais séries cobrem 2012Q1 em
    diante. A tabela 6402 é usada (e não a 6385/6386) porque só ela tem a
    série contínua de pessoas ocupadas, inclusive 2020Q2–2021Q4.
    """
    regs = []
    for row in _get(MERCADO_TRABALHO)[1:]:
        codigo = row.get("D2C", "")
        if codigo not in VARIAVEIS_TRABALHO:
            continue
        valor = _valor(row)
        periodo = row.get("D3C", "")
        if valor is None or not periodo:
            continue
        variavel, conceito = VARIAVEIS_TRABALHO[codigo]
        regs.append({
            "data": _data_trimestre(periodo),
            "periodo_codigo": periodo,
            "periodo_rotulo": row.get("D3N"),
            "variavel": variavel,
            "conceito": conceito,
            "valor": valor,
            "unidade": row.get("MN", ""),
        })
    df = pd.DataFrame(regs).sort_values(
        ["variavel", "data"]).reset_index(drop=True)

    if df.empty:
        raise ValueError("Mercado de trabalho: nenhuma linha")
    dup = df.duplicated(["data", "variavel"])
    if dup.any():
        raise ValueError(
            f"Mercado de trabalho: {int(dup.sum())} trimestres duplicados")
    esperadas = {v[0] for v in VARIAVEIS_TRABALHO.values()}
    if set(df["variavel"]) != esperadas:
        raise ValueError(
            "Mercado de trabalho: variáveis faltando "
            f"({sorted(esperadas - set(df['variavel']))})")
    contagem = df.groupby("variavel")["data"].nunique()
    for variavel in ("ocupados_mil", "participacao_pct",
                     "nivel_ocupacao_pct"):
        if contagem.get(variavel, 0) < 55:
            raise ValueError(
                f"Mercado de trabalho: {variavel} com "
                f"{contagem.get(variavel, 0)} trimestres (esperado >= 55)")
    if contagem.get("informalidade_pct", 0) < 40:
        raise ValueError(
            "Mercado de trabalho: informalidade com "
            f"{contagem.get('informalidade_pct', 0)} trimestres "
            "(esperado >= 40)")
    if df["data"].max() < pd.Timestamp("2025-12-31"):
        raise ValueError(
            f"Mercado de trabalho: série termina em {df['data'].max()} "
            "(esperado >= 2025Q4)")
    for variavel, grupo in df.groupby("variavel"):
        gaps = grupo["data"].sort_values().diff().dropna().dt.days
        if not gaps.between(80, 100).all():
            raise ValueError(
                f"Mercado de trabalho: buraco na série {variavel} "
                f"(gaps de {gaps.min()} a {gaps.max()} dias)")
    taxas = df[df["variavel"] != "ocupados_mil"]
    if not taxas["valor"].between(0, 100).all():
        raise ValueError("Mercado de trabalho: taxa fora de 0–100%")
    ocupados = df.loc[df["variavel"] == "ocupados_mil", "valor"]
    if (ocupados <= 0).any():
        raise ValueError("Mercado de trabalho: pessoas ocupadas <= 0")
    return salvar_parquet(df, "mercado_trabalho")


def main() -> None:
    for rotina in (processar, processar_rendimento, processar_fbcf,
                   processar_ipca_grupos, processar_produtividade,
                   processar_mercado_trabalho):
        out = rotina()
        df = pd.read_parquet(out)
        col_data = "data"
        print(
            f"{rotina.__name__}: {len(df)} linhas, "
            f"{df[col_data].min().date()} -> {df[col_data].max().date()}"
        )


if __name__ == "__main__":
    main()
