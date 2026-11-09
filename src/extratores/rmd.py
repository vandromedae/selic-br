"""Extrator RMD — Anexos do Relatório Mensal da Dívida Pública Federal (STN).

O anexo ZIP (thot-arquivos.tesouro.gov.br/publicacao-anexo/{id}) contém um XLSX
com séries históricas. Extrações principais:

- 2.7  Detentores da DPMFi (R$ bi e participação) — desde 2007   -> rmd_detentores
- 4.1/4.2/4.3 Custo médio (% a.a.)                               -> rmd_custo_medio
- 5.5  Composição da DPMFi por indexador, após swap (desde 1999) -> rmd_composicao
- 6.1  Reserva de liquidez                                       -> rmd_reserva

Descoberta do último anexo: tenta a página do RMD; se o portal estiver em
manutenção, sonda janela de ids no thot-arquivos atrás de redirect cujo
arquivo seja "Anexo ... RMD ....zip".
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

from .base import BRUTO, get, salvar_parquet

RMD_PAGE = "https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd"
THOT = "https://thot-arquivos.tesouro.gov.br/publicacao-anexo/{id}"
ESTADO = BRUTO / "rmd" / "ultimo_anexo.json"
XLSX_CACHE = BRUTO / "rmd" / "anexo_rmd.xlsx"

_MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
_RE_MES = re.compile(r"^([A-Za-z]{3})/(\d{2})$")
_RE_ANO = re.compile(r"^\d{4}$")
_UA = {"User-Agent": "Mozilla/5.0 (juros-e-divida/1.0)"}


def _ids_conhecidos() -> list[int]:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text()).get("ids", [])
    return []


def _salvar_id(anexo_id: int, url: str) -> None:
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({"ids": [anexo_id], "url": url}, ensure_ascii=False))


def _location(url: str) -> str | None:
    try:
        r = requests.head(url, headers=_UA, allow_redirects=False, timeout=30)
        if r.status_code in (301, 302, 303, 307, 308):
            return r.headers.get("Location")
    except requests.RequestException:
        return None
    return None


def descobrir_anexo() -> tuple[int, str]:
    """Retorna (id, url_download) do anexo ZIP mais recente do RMD."""
    # 1) página oficial do RMD (quando disponível)
    try:
        html = get(RMD_PAGE, timeout=45).decode("utf-8", "ignore")
        for m in sorted(set(re.findall(r"publicacao-anexo/(\d+)", html)), key=int):
            loc = _location(THOT.format(id=m))
            if loc and ".zip" in unquote(loc).lower() and "rmd" in unquote(loc).lower():
                return int(m), loc
    except Exception:
        pass

    # 2) sonda de ids acima do último conhecido (portal em manutenção)
    base = max(_ids_conhecidos() or [29569])
    melhor: tuple[int, str] | None = None
    for pid in range(base, base + 120):
        loc = _location(THOT.format(id=pid))
        if not loc:
            continue
        nome = unquote(loc).lower()
        if ".zip" in nome and "anexo" in nome and "rmd" in nome:
            melhor = (pid, loc)
    if melhor:
        return melhor
    if _ids_conhecidos():
        raise RuntimeError("nenhum anexo RMD novo encontrado; portal em manutenção?")
    raise RuntimeError("nenhum anexo RMD encontrado")


def baixar(force: bool = False) -> Path:
    """Baixa o último anexo ZIP e extrai o XLSX para cache."""
    if XLSX_CACHE.exists() and not force:
        return XLSX_CACHE
    anexo_id, url = descobrir_anexo()
    print(f"anexo RMD id={anexo_id} <- {url[:100]}", flush=True)
    content = get(url, timeout=180)
    XLSX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        nomes = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if not nomes:
            raise RuntimeError("ZIP sem XLSX")
        XLSX_CACHE.write_bytes(zf.read(nomes[0]))
    _salvar_id(anexo_id, url)
    return XLSX_CACHE


# ----------------------------------------------------------------- parse helpers


def _acha_cabecalho_meses(bruto: pd.DataFrame) -> int:
    for i in range(min(15, len(bruto))):
        n = sum(
            1 for j in range(bruto.shape[1])
            if isinstance(bruto.iloc[i, j], str) and _RE_MES.match(bruto.iloc[i, j].strip())
        )
        if n >= 6:
            return i
    raise ValueError("cabeçalho de meses não encontrado")


def _melte_largo(bruto: pd.DataFrame) -> pd.DataFrame:
    """XLSX largo (label em col0, meses nas colunas) -> longo."""
    linha = _acha_cabecalho_meses(bruto)
    cab = bruto.iloc[linha]
    cols = [
        j for j in range(1, bruto.shape[1])
        if isinstance(cab.iloc[j], str) and _RE_MES.match(cab.iloc[j].strip())
    ]
    regs = []
    for i in range(linha + 1, len(bruto)):
        label = str(bruto.iloc[i, 0]).strip()
        if label in ("nan", ""):
            continue
        for j in cols:
            val = bruto.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):  # 'N/D' etc.
                continue
            m = _RE_MES.match(cab.iloc[j].strip())
            if not m:
                continue
            ano = 2000 + int(m.group(2))
            regs.append({
                "indicador": label,
                "data": pd.Timestamp(ano, _MESES[m.group(1).lower()], 1) + pd.offsets.MonthEnd(0),
                "valor": v,
            })
    return pd.DataFrame(regs)


def _melte_pares(bruto: pd.DataFrame, cab_row: int = 4, data_row0: int = 5) -> pd.DataFrame:
    """Layout 'pares' (col0=data, col1=valor, col2=share, col3=valor, ...)."""
    cab = bruto.iloc[cab_row]
    grupos = [j for j in range(1, bruto.shape[1]) if str(cab.iloc[j]) != "nan"]
    regs = []
    for i in range(data_row0, len(bruto)):
        d = bruto.iloc[i, 0]
        if pd.isna(d) or not isinstance(d, (pd.Timestamp,)):
            # aceita strings de data também
            try:
                d = pd.Timestamp(d)
            except Exception:
                continue
        if pd.isna(d):
            continue  # linha em branco do Excel (pd.Timestamp(NaT) não falha)
        for j in grupos:
            nome = str(cab.iloc[j]).strip()
            if nome == "nan":
                continue
            val = bruto.iloc[i, j]
            share = bruto.iloc[i, j + 1] if j + 1 < bruto.shape[1] else float("nan")
            try:
                v = float(val) if not pd.isna(val) else float("nan")
            except (TypeError, ValueError):
                v = float("nan")
            try:
                p = float(share) if not pd.isna(share) else float("nan")
            except (TypeError, ValueError):
                p = float("nan")
            if pd.isna(v) and pd.isna(p):
                continue  # mês sem dado para este grupo
            regs.append({
                "data": pd.Timestamp(d) + pd.offsets.MonthEnd(0),
                "grupo": nome,
                "valor_bi": v,
                "participacao": p,
            })
    return pd.DataFrame(regs)


def _ler(sheet: str) -> pd.DataFrame:
    return pd.read_excel(XLSX_CACHE, sheet_name=sheet, header=None)


# --------------------------------------------------------------- processamentos


def processar_detentores() -> pd.DataFrame:
    df = _melte_pares(_ler("2.7"))
    df = df.rename(columns={"grupo": "detentor"})
    # remove notas de rodapé dos nomes ("Previdência 3" -> "Previdência")
    df["detentor"] = df["detentor"].str.replace(r"\s+\d+$", "", regex=True)
    df["unidade"] = "R$ bilhões (estoque DPMFi em mercado)"
    return salvar_parquet(df, "rmd_detentores")


def processar_custo_medio() -> pd.DataFrame:
    frames = []
    for sheet, rotulo in [("4.1", "estoque mensal"), ("4.2", "estoque 12m"),
                          ("4.3", "emissões 12m")]:
        try:
            d = _melte_largo(_ler(sheet))
        except ValueError:
            continue
        d["tabela"] = rotulo
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns={"indicador": "escopo", "valor": "taxa_pct_aa"})
    df["unidade"] = "% a.a."
    return salvar_parquet(df, "rmd_custo_medio")


def processar_composicao() -> pd.DataFrame:
    df = _melte_pares(_ler("5.5"))
    df = df.rename(columns={"grupo": "indexador"})
    df["unidade"] = "R$ bilhões (após swap)"
    return salvar_parquet(df, "rmd_composicao")


def processar_reserva() -> pd.DataFrame:
    bruto = _ler("6.1")
    cab = bruto.iloc[4]  # Mês | Reserva | Valor Prudencial | Índice
    cols = [j for j in range(1, bruto.shape[1]) if str(cab.iloc[j]) != "nan"]
    regs = []
    for i in range(6, len(bruto)):
        d = bruto.iloc[i, 0]
        if pd.isna(d):
            continue
        for j in cols:
            val = bruto.iloc[i, j]
            if pd.isna(val):
                continue
            regs.append({
                "data": pd.Timestamp(d) + pd.offsets.MonthEnd(0),
                "indicador": str(cab.iloc[j]).strip(),
                "valor": float(val),
            })
    return salvar_parquet(pd.DataFrame(regs), "rmd_reserva")


def main(force: bool = False) -> None:
    baixar(force=force)
    for fn in (processar_detentores, processar_custo_medio,
               processar_composicao, processar_reserva):
        out = fn()
        n = len(pd.read_parquet(out)) if isinstance(out, Path) else len(out)
        print(f"{fn.__name__}: {n} linhas")


if __name__ == "__main__":
    import sys

    main(force="--force" in sys.argv)
