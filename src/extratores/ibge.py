"""Extrator IBGE (SIDRA) — mercado de trabalho.

Tabela 6381, variável 4099: taxa de desocupação (PNAD Contínua, 3 meses
móvel), Brasil -> desemprego.parquet.
"""

from __future__ import annotations

import time

import pandas as pd
import requests

from .base import salvar_parquet

SIDRA = "https://apisidra.ibge.gov.br/values/t/6381/n1/all/v/4099/p/all?formato=json"
_UA = {"User-Agent": "juros-e-divida/1.0"}


def baixar() -> list[dict]:
    for tentativa in range(4):
        try:
            r = requests.get(SIDRA, headers=_UA, timeout=120)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if tentativa == 3:
                raise
            time.sleep(2 * (tentativa + 1))
    raise RuntimeError("sidra")


def processar() -> pd.DataFrame:
    bruto = baixar()
    cab, *linhas = bruto  # primeira linha = cabeçalho
    regs = []
    for row in linhas:
        periodo = row.get("D3C", "")
        valor = row.get("V", "")
        # SIDRA: "-", "..." (dado indisponível) e "X" (confidencial) não são número
        if not periodo or valor in ("-", "...", "X", None, ""):
            continue
        # D3C = AAAAMM do último mês do trimestre móvel
        data = pd.Timestamp(int(periodo[:4]), int(periodo[4:]), 1) + pd.offsets.MonthEnd(0)
        regs.append({
            "data": data,
            "periodo_codigo": periodo,
            "periodo_rotulo": row.get("D3N"),
            "taxa_pct": float(valor.replace(",", ".")),
        })
    df = pd.DataFrame(regs).sort_values("data").reset_index(drop=True)
    df["unidade"] = "% (3 meses móveis)"
    return salvar_parquet(df, "desemprego")


def main() -> None:
    out = processar()
    df = pd.read_parquet(out)
    print(f"processar: {len(df)} linhas, {df.data.min().date()} -> {df.data.max().date()}")


if __name__ == "__main__":
    main()
