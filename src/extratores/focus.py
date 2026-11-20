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
MAX_PAGINAS = 400  # teto de segurança: 400 × 5000 = 2M registros


def _odata(endpoint: str, filtro: str | None = None,
           orderby: str | None = None) -> list[dict]:
    """GET paginado de um entityset OData ($top/$skip, ou @odata.nextLink).

    Monta a query manualmente: o Olinda rejeita '+' como espaço (requests
    usa urlencoding com '+'); precisa ser %20.

    A paginação assume o mínimo possível do servidor:
    - `orderby` determinístico (chave do entityset) para $skip não pular
      nem repetir linhas em empates;
    - fim = página VAZIA (não "lote menor que $top"): servidor que limita
      o lote não faz o extrator perder dados em silêncio;
    - página repetida = servidor ignorou $skip -> erro claro, não loop
      infinito acumulando duplicatas;
    - resposta fora do formato {"value": [dict, ...]} -> erro claro;
    - @odata.nextLink seguido quando o servidor oferece (o Olinda hoje
      não oferece; $skip é o fallback);
    - teto MAX_PAGINAS contra loop infinito; total coletado registrado.
    """
    q = f"$format=json&$top={TOP}"
    if filtro:
        q += f"&$filter={quote(filtro, safe='')}"
    if orderby:
        q += f"&$orderby={quote(orderby, safe=',')}"
    url = f"{BASE}/{endpoint}?{q}&$skip=0"

    registros: list[dict] = []
    lote_anterior: list[dict] | None = None
    paginas = 0
    while True:
        for tentativa in range(4):
            try:
                r = requests.get(url, headers=_UA, timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException:
                if tentativa == 3:
                    raise
                time.sleep(2 * (tentativa + 1))
        try:
            corpo = r.json()
        except ValueError:
            corpo = None
        if (not isinstance(corpo, dict)
                or not isinstance(corpo.get("value"), list)
                or (corpo["value"] and not isinstance(corpo["value"][0], dict))):
            raise RuntimeError(
                f"{endpoint}: resposta fora do formato OData esperado em {url}")
        lote = corpo["value"]
        if lote_anterior is not None and lote == lote_anterior:
            raise RuntimeError(
                f"{endpoint}: página repetida em {url} — o servidor ignorou "
                f"$skip? ({len(registros)} registros coletados até aqui)")
        lote_anterior = lote
        if not lote:
            break
        registros.extend(lote)
        paginas += 1
        if paginas > MAX_PAGINAS:
            raise RuntimeError(
                f"{endpoint}: teto de {MAX_PAGINAS} páginas atingido "
                f"({len(registros)} registros) — loop infinito na paginação?")
        nxt = corpo.get("@odata.nextLink") or corpo.get("odata.nextLink")
        url = nxt or f"{BASE}/{endpoint}?{q}&$skip={len(registros)}"
        time.sleep(0.3)
    print(f"  {endpoint}: {len(registros)} registros em {paginas} página(s)")
    return registros


def processar_anuais() -> pd.DataFrame:
    regs = []
    for indicador in ("IPCA", "Selic"):
        for row in _odata(
            "ExpectativasMercadoAnuais",
            f"Indicador eq '{indicador}' and DataReferencia ge '2000'",
            orderby="Data,DataReferencia,IndicadorDetalhe",
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
        orderby="Data,Suavizada",
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
    for row in _odata("ExpectativasMercadoSelic", orderby="Data,Reuniao"):
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
