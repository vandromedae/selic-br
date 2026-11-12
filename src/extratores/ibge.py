"""Extrator IBGE (SIDRA) — mercado de trabalho, rendimento e investimento.

Tabelas:
- 6381, variável 4099: taxa de desocupação (PNAD Contínua, 3 meses
  móvel), Brasil -> desemprego.parquet.
- 4660/4663/5436: rendimento médio mensal e massa de rendimento da PNAD
  Contínua (anual e trimestral, desde 2012) -> rendimento.parquet.
- 1620, classificação 11255: índice de volume trimestral do PIB e da
  Formação Bruta de Capital Fixo (Contas Nacionais Trimestrais, base
  média 1995 = 100) -> fbcf.parquet.

A API do SIDRA exige a classificação "Setores e subsetores" (c11255) nas
tabelas da CNT; sem ela, todos os valores vêm como ".." (não se aplica).
"""

from __future__ import annotations

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


def main() -> None:
    for rotina in (processar, processar_rendimento, processar_fbcf):
        out = rotina()
        df = pd.read_parquet(out)
        col_data = "data"
        print(
            f"{rotina.__name__}: {len(df)} linhas, "
            f"{df[col_data].min().date()} -> {df[col_data].max().date()}"
        )


if __name__ == "__main__":
    main()
