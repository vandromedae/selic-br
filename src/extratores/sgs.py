"""Extrai séries do SGS/BCB para dados/processado/sgs.parquet (formato longo).

Uso:  python -m src.extratores.sgs [codigo ...]   (sem argumentos = todas)
"""
from __future__ import annotations

import sys
import time

import pandas as pd

from .base import get_json, salvar_parquet
from .catalogo_sgs import SERIES_SGS

API = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={ini}&dataFinal={fim}"
INICIO = 2002  # janela da análise


def _baixar_janela(codigo: int, ini: str, fim: str) -> list[dict]:
    url = API.format(codigo=codigo, ini=ini, fim=fim)
    # 404 = "Value(s) not found": janela anterior ao início da série
    return get_json(url, ignorar_404=True)


def _fim_de(ano: int) -> str:
    """Data final válida: nunca além de hoje (a API devolve 304 vazio se futura)."""
    from datetime import date

    hoje = date.today()
    if ano < hoje.year:
        return f"31/12/{ano}"
    return hoje.strftime("%d/%m/%Y")  # ano atual ou futuro: até hoje


def baixar_serie(codigo: int) -> pd.DataFrame:
    """Baixa série; séries diárias são paginadas ano a ano (a API trunca)."""
    meta = SERIES_SGS[codigo]
    registros: list[dict] = []
    if meta["freq"] == "D":
        from datetime import date

        ultimo_ano = date.today().year
        for ano in range(INICIO, ultimo_ano + 1):
            fim = _fim_de(ano)
            ini = f"01/01/{ano}"
            if ini > fim:
                break
            registros += _baixar_janela(codigo, ini, fim)
            time.sleep(0.3)
    else:
        from datetime import date

        ultimo_ano = date.today().year
        # mensais: janelas de 5 anos evitam truncamento silencioso
        for ini_ano in range(INICIO, ultimo_ano + 1, 5):
            fim_ano = min(ini_ano + 4, ultimo_ano)
            registros += _baixar_janela(codigo, f"01/01/{ini_ano}", _fim_de(fim_ano))
            time.sleep(0.3)
    if not registros:
        raise ValueError(f"SGS {codigo}: resposta vazia")
    df = pd.DataFrame(registros)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["codigo_sgs"] = codigo
    df["serie"] = meta["nome"]
    df["descricao"] = meta["desc"]
    return df[["data", "codigo_sgs", "serie", "descricao", "valor"]].drop_duplicates()


def main(codigos: list[int] | None = None) -> pd.DataFrame:
    codigos = codigos or list(SERIES_SGS)
    frames = []
    for cod in codigos:
        print(f"SGS {cod} ({SERIES_SGS[cod]['nome']}) ...", flush=True)
        frames.append(baixar_serie(cod))
        time.sleep(0.4)
    novo = pd.concat(frames, ignore_index=True)
    # mescla com o que já existe (permite baixar só séries novas)
    try:
        from .base import ler_parquet

        existente = ler_parquet("sgs")
        existente = existente[~existente["serie"].isin(novo["serie"].unique())]
        df = pd.concat([existente, novo], ignore_index=True)
    except FileNotFoundError:
        df = novo
    df = df.sort_values(["serie", "data"]).reset_index(drop=True)
    caminho = salvar_parquet(df, "sgs")
    print(f"OK -> {caminho} ({len(df)} linhas, {df['serie'].nunique()} séries)")
    return df


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]]
    main(args or None)
