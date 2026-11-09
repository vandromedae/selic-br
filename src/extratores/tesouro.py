"""Extrator Tesouro Nacional (Portal da Transparência, CKAN).

Datasets:
- estoque-da-divida-publica-federal           -> estoque.xlsx (anexo 2.1, R$ bilhões)
                                                + estoque.csv (título a título)
- fatores-de-variacao-da-divida-publica-federal -> fatores.xlsx (anexo 2.9, R$ milhões)
- emissoes-e-resgates-divida-publica-federal   -> emissoes.xlsx (anexo 1.1, R$ milhões)

Os XLSX são "anexos" largos (linhas = indicadores, colunas = meses);
aqui são derretidos para formato longo e salvos em parquet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

from .base import BRUTO, PROCESSADO, salvar_parquet

CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"

PAQUETES = {
    "estoque": "estoque-da-divida-publica-federal",
    "fatores": "fatores-de-variacao-da-divida-publica-federal",
    "emissoes": "emissoes-e-resgates-divida-publica-federal",
}

MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
_RE_MES = re.compile(r"^([A-Za-z]{3})/(\d{2})$")
_RE_ANO = re.compile(r"^\d{4}$")


def _descobrir_url(pid: str, fmts=("XLSX", "CSV")) -> dict[str, str]:
    """Retorna {ext: url} dos recursos não-metadados do pacote."""
    r = requests.get(CKAN, params={"id": pid}, timeout=60)
    r.raise_for_status()
    recursos: dict[str, str] = {}
    for res in r.json()["result"]["resources"]:
        fmt = (res.get("format") or "").upper()
        nome = res.get("name") or ""
        if fmt in fmts and "Metadados" not in nome:
            recursos[fmt.lower()] = res["url"]
    return recursos


def baixar(force: bool = False) -> dict[str, Path]:
    """Baixa os arquivos brutos (com cache em dados/bruto/tesouro)."""
    destino = BRUTO / "tesouro"
    destino.mkdir(parents=True, exist_ok=True)
    baixados: dict[str, Path] = {}
    for nome, pid in PAQUETES.items():
        for ext, url in _descobrir_url(pid).items():
            caminho = destino / f"{nome}.{ext}"
            if force or not caminho.exists():
                print(f"baixando {caminho.name} <- {url[:90]}...", flush=True)
                resp = requests.get(url, timeout=180)
                resp.raise_for_status()
                caminho.write_bytes(resp.content)
            baixados[caminho.name] = caminho
    return baixados


def _acha_cabecalho(df: pd.DataFrame) -> int:
    """Índice da linha do cabeçalho (contém meses 'Jan/07' em ≥6 colunas)."""
    for i in range(min(15, len(df))):
        meses = [
            j for j in range(df.shape[1])
            if isinstance(df.iloc[i, j], str) and _RE_MES.match(str(df.iloc[i, j]).strip())
        ]
        if len(meses) >= 6:
            return i
    raise ValueError("cabeçalho de meses não encontrado")


def _melte_anexo(caminho: Path, sheet=0) -> pd.DataFrame:
    """XLSX largo (label em col0, meses/anos nas colunas) -> longo."""
    bruto = pd.read_excel(caminho, sheet_name=sheet, header=None)
    linha = _acha_cabecalho(bruto)
    cab = bruto.iloc[linha]
    cols_mes, cols_ano = [], []
    for j in range(1, bruto.shape[1]):
        v = cab.iloc[j]
        if pd.isna(v):
            continue
        s = str(v).strip()
        if _RE_MES.match(s):
            cols_mes.append(j)
        elif _RE_ANO.match(s):  # colunas anuais vêm como int (2007) ou str
            cols_ano.append(j)

    registros = []
    for i in range(linha + 1, len(bruto)):
        label = str(bruto.iloc[i, 0])
        if label in ("nan", "") or label.strip() == "":
            continue
        label = label.strip()
        if label.startswith(("¹", "2 ", "1 ", "OBS", "3 ", "4 ")):
            continue
        for j in cols_mes:
            val = bruto.iloc[i, j]
            if pd.isna(val):
                continue
            m = _RE_MES.match(str(cab.iloc[j]).strip())
            if not m:
                continue
            ano = 2000 + int(m.group(2))
            registros.append({
                "indicador": label,
                "data": pd.Timestamp(ano, MESES[m.group(1).lower()], 1) + pd.offsets.MonthEnd(0),
                "periodo": "mensal",
                "valor": float(val),
            })
        for j in cols_ano:
            val = bruto.iloc[i, j]
            if pd.isna(val):
                continue
            registros.append({
                "indicador": label,
                "data": pd.Timestamp(int(str(cab.iloc[j]).strip()), 12, 31),
                "periodo": "anual",
                "valor": float(val),
            })
    return pd.DataFrame.from_records(registros)


def processar_estoque() -> pd.DataFrame:
    df = _melte_anexo(BRUTO / "tesouro" / "estoque.xlsx")
    df = df.rename(columns={"indicador": "linha", "valor": "valor_bi"})
    df["unidade"] = "R$ bilhões"
    return salvar_parquet(df, "tesouro_estoque")


def processar_fatores() -> pd.DataFrame:
    df = _melte_anexo(BRUTO / "tesouro" / "fatores.xlsx")
    df = df.rename(columns={"indicador": "fator", "valor": "valor_mi"})
    df["unidade"] = "R$ milhões"
    return salvar_parquet(df, "tesouro_fatores")


def processar_emissoes() -> pd.DataFrame:
    df = _melte_anexo(BRUTO / "tesouro" / "emissoes.xlsx")
    df = df.rename(columns={"indicador": "operacao", "valor": "valor_mi"})
    df["unidade"] = "R$ milhões"
    return salvar_parquet(df, "tesouro_emissoes")


def processar_estoque_csv() -> pd.DataFrame:
    """Estoque título a título -> agregado por mês × classe × tipo de dívida."""
    caminho = BRUTO / "tesouro" / "estoque.csv"
    if not caminho.exists():
        return pd.DataFrame()
    df = pd.read_csv(
        caminho, sep=None, engine="python",
        dtype={"Valor do Estoque": str, "Mes do Estoque": str},
    )
    # valores do CSV vêm em R$ cheios (vírgula decimal); converte para R$ milhões
    df["valor_mi"] = (
        df["Valor do Estoque"].str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False).astype(float) / 1e6
    )
    df["data"] = pd.to_datetime(df["Mes do Estoque"], format="%m/%Y") + pd.offsets.MonthEnd(0)
    agg = (
        df.groupby(["data", "Classe da Carteira", "Tipo de Divida"], as_index=False)
        .agg(valor_mi=("valor_mi", "sum"), titulos=("Titulo/Contrato", "nunique"))
    )
    return salvar_parquet(agg, "tesouro_estoque_titulos")


def main() -> None:
    baixar()
    for fn in (processar_estoque, processar_fatores, processar_emissoes,
               processar_estoque_csv):
        out = fn()
        if isinstance(out, Path):
            n = len(pd.read_parquet(out))
            print(f"{fn.__name__}: {n} linhas -> {out.name}")


if __name__ == "__main__":
    main()
