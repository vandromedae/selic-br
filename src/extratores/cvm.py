"""Extrator CVM — carteira dos fundos de investimento (CDA).

Fonte: dados abertos da CVM, `FI/DOC/CDA/DADOS/cda_fi_YYYYMM.zip`
(documento de carteira mensal, por bloco de posição). O bloco `BLC_1`
traz os ativos em carteira; filtramos `TP_APLIC == "Títulos Públicos"`,
que nomeia cada fundo (`DENOM_SOCIAL`) e a sua posição em títulos
federais — o "nome aos bois" dos beneficiários da dívida.

O que este dado NÃO cobre: a previdência fechada (fundos de pensão
patronais, regulados pela PREVIC) não é fundo CVM; os fundos exclusivos
estão em `cda_fie_*` (fora deste extrator).

Saída: `cvm_fundos_titulos.parquet` (fundos nomeados × tipo de título).
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

from .base import BRUTO, salvar_parquet

RAIZ = Path(__file__).resolve().parents[2]
CVM_CDA = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/"
CACHE = BRUTO / "cvm"


def _descobrir_meses() -> list[str]:
    r = requests.get(CVM_CDA, timeout=60)
    r.raise_for_status()
    return sorted(set(re.findall(r"cda_fi_(\d{6})\.zip", r.text)))


def baixar(mes: str | None = None) -> Path:
    """Baixa o CDA do mês (YYYYMM); padrão: o último disponível."""
    if mes is None:
        mes = _descobrir_meses()[-1]
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"cda_fi_{mes}.zip"
    if not destino.exists() or destino.stat().st_size == 0:
        u = f"{CVM_CDA}{destino.name}"
        resp = requests.get(u, timeout=300)
        resp.raise_for_status()
        destino.write_bytes(resp.content)
    return destino


def processar_fundos_titulos(mes: str | None = None) -> pd.DataFrame:
    """Posição em títulos públicos por fundo nomeado (bloco BLC_1)."""
    caminho = baixar(mes)
    ref = caminho.stem.split("_")[-1]  # YYYYMM
    with zipfile.ZipFile(caminho) as zf:
        nome = next((n for n in zf.namelist() if n.startswith("cda_fi_BLC_1")), None)
        if nome is None:
            raise ValueError(f"{caminho.name}: bloco BLC_1 ausente — "
                             f"arquivos: {zf.namelist()}")
        bruto = pd.read_csv(zf.open(nome), sep=";", encoding="latin-1",
                            low_memory=False)
    for col in ("TP_APLIC", "DENOM_SOCIAL", "VL_MERC_POS_FINAL", "TP_TITPUB"):
        if col not in bruto.columns:
            raise ValueError(
                f"cvm CDA {ref}: coluna {col!r} ausente — "
                f"encontradas: {sorted(bruto.columns)}")
    tp = bruto[bruto.TP_APLIC == "Títulos Públicos"].copy()
    if tp.empty:
        raise ValueError(f"cvm CDA {ref}: filtro 'Títulos Públicos' não casou "
                         "nenhuma linha — a classificação mudou?")
    df = tp.groupby(["DENOM_SOCIAL", "TP_TITPUB"], as_index=False).agg(
        valor_bi=("VL_MERC_POS_FINAL", lambda s: float(s.sum()) / 1e9))
    df = df.rename(columns={"DENOM_SOCIAL": "fundo", "TP_TITPUB": "titulo"})
    df["mes"] = pd.Period(ref, freq="M").to_timestamp() + pd.offsets.MonthEnd(0)
    return salvar_parquet(df, "cvm_fundos_titulos")


def main() -> None:
    out = processar_fundos_titulos()
    processar_carteira_pais()
    df = pd.read_parquet(out)
    total = df.valor_bi.sum()
    print(f"cvm_fundos_titulos: {len(df)} linhas | "
          f"{df.fundo.nunique()} fundos | R$ {total:,.0f} bi em títulos públicos")
    top = df.groupby("fundo").valor_bi.sum().nlargest(10)
    print("maiores fundos (R$ bi):")
    for nome, v in top.items():
        print(f"  {v:8.1f}  {nome[:70]}")


CARTEIRA_PAIS = ("https://www.gov.br/cvm/pt-br/centrais-de-conteudo/publicacoes/"
                 "series-historicas/investimento-estrangeiro/"
                 "carteira-x-pais_dez2024.xls")


def processar_carteira_pais() -> pd.DataFrame:
    """Carteira de investidores não residentes por país de domicílio (CVM).

    O arquivo traz a posição por tipo de ativo; usamos a coluna de
    títulos públicos federais — nomeia de onde vem o capital estrangeiro
    que financia a dívida. Atenção: a linha "Total Geral" é um total do
    próprio arquivo e precisa ser excluída das somas.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / "cvm_carteira_pais.xls"
    if not destino.exists() or destino.stat().st_size == 0:
        resp = requests.get(CARTEIRA_PAIS, allow_redirects=True, timeout=180)
        resp.raise_for_status()
        destino.write_bytes(resp.content)
    bruto = pd.read_excel(destino, sheet_name=0, header=None)
    # cabeçalho: a linha com 'PAÍS DE DOMICÍLIO'; a coluna de títulos federais
    cab_i = next(i for i in range(len(bruto))
                 if isinstance(bruto.iloc[i, 0], str)
                 and "PAÍS" in bruto.iloc[i, 0])
    cab = [str(v) for v in bruto.iloc[cab_i]]
    j_tpf = next(j for j, v in enumerate(cab)
                 if "públicos federais" in v)
    corpo = bruto.iloc[cab_i + 1:].copy()
    corpo.columns = cab
    df = pd.DataFrame({
        "pais": corpo.iloc[:, 0].astype(str).str.strip(),
        "valor_bi": pd.to_numeric(bruto.iloc[cab_i + 1:, j_tpf],
                                  errors="coerce") / 1e9,
    })
    df = df[df.pais.notna() & (df.pais != "nan")]
    df = df[~df.pais.str.contains("Total", case=False, na=False)]
    df = df[df.valor_bi.notna() & (df.valor_bi > 0)]
    if df.empty:
        raise ValueError("cvm carteira por país: nenhum dado — o arquivo mudou?")
    df["mes"] = pd.Timestamp("2024-12-31")
    return salvar_parquet(df.reset_index(drop=True), "cvm_carteira_pais")


if __name__ == "__main__":
    sys.exit(main())
