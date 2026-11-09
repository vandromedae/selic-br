"""Extrator Focus / Expectativas de Mercado (Olinda, BCB).

Endpoints (OData v1):
- ExpectativasMercadoAnuais: IPCA e Selic, expectativas por ano-calendário
  (desde 2000) -> focus_anuais.parquet
- ExpectativasMercadoInflacao12Meses: expectativa de inflação 12 meses à frente
  (desde 2001) -> focus_inflacao12m.parquet
- ExpectativasMercadoSelic: expectativas de Selic -> focus_selic.parquet
"""

from __future__ import annotations

import time
from urllib.parse import quote

import pandas as pd
import requests

from .base import salvar_parquet

BASE = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata")
_UA = {"User-Agent": "juros-e-divida/1.0", "Accept": "application/json"}
TOP = 5000


def _odata(endpoint: str, filtro: str | None = None) -> list[dict]:
    """GET paginado ($top/$skip) de um entityset OData.

    Monta a query manualmente: o Olinda rejeita '+' como espaço (requests
    usa urlencoding com '+'); precisa ser %20.
    """
    registros: list[dict] = []
    skip = 0
    while True:
        q = f"$format=json&$top={TOP}&$skip={skip}"
        if filtro:
            q += f"&$filter={quote(filtro, safe='')}"
        url = f"{BASE}/{endpoint}?{q}"
        for tentativa in range(4):
            try:
                r = requests.get(url, headers=_UA, timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException:
                if tentativa == 3:
                    raise
                time.sleep(2 * (tentativa + 1))
        lote = r.json().get("value", [])
        registros.extend(lote)
        if len(lote) < TOP:
            return registros
        skip += TOP
        time.sleep(0.3)


def processar_anuais() -> pd.DataFrame:
    regs = []
    for indicador in ("IPCA", "Selic"):
        for row in _odata(
            "ExpectativasMercadoAnuais",
            f"Indicador eq '{indicador}' and DataReferencia ge '2000'",
        ):
            regs.append({
                "indicador": row["Indicador"],
                "data_pesquisa": pd.Timestamp(row["Data"]),
                "data_referencia": int(row["DataReferencia"]),
                "media": row.get("Media"),
                "mediana": row.get("Mediana"),
                "minimo": row.get("Minimo"),
                "maximo": row.get("Maximo"),
                "desvio_padrao": row.get("DesvioPadrao"),
                "respondentes": row.get("numeroRespondentes"),
            })
        time.sleep(0.3)
    df = pd.DataFrame(regs)
    return salvar_parquet(df, "focus_anuais")


def processar_inflacao12m() -> pd.DataFrame:
    regs = []
    for row in _odata(
        "ExpectativasMercadoInflacao12Meses",
        "Indicador eq 'IPCA'",
    ):
        regs.append({
            "data_pesquisa": pd.Timestamp(row["Data"]),
            "media": row.get("Media"),
            "mediana": row.get("Mediana"),
            "minimo": row.get("Minimo"),
            "maximo": row.get("Maximo"),
            "desvio_padrao": row.get("DesvioPadrao"),
            "suavizada": row.get("Suavizada"),
            "respondentes": row.get("numeroRespondentes"),
        })
    df = pd.DataFrame(regs)
    return salvar_parquet(df, "focus_inflacao12m")


def processar_selic() -> pd.DataFrame:
    regs = []
    for row in _odata("ExpectativasMercadoSelic"):
        regs.append({k: v for k, v in row.items()})
    df = pd.DataFrame(regs)
    for col in ("Data", "DataReferencia"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return salvar_parquet(df, "focus_selic")


def main() -> None:
    for fn in (processar_anuais, processar_inflacao12m, processar_selic):
        out = fn()
        print(f"{fn.__name__}: {len(pd.read_parquet(out))} linhas -> {out.name}")


if __name__ == "__main__":
    main()
