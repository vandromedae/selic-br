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

from datetime import date
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

from .base import (BRUTO, MESES, RE_MES, ano_de_dois_digitos, get,
                    meta_gravar, meta_ler, salvar_parquet,
                    usar_cache as _usar_cache_arquivo)

RMD_PAGE = "https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd"
THOT = "https://thot-arquivos.tesouro.gov.br/publicacao-anexo/{id}"
ESTADO = BRUTO / "rmd" / "ultimo_anexo.json"
XLSX_CACHE = BRUTO / "rmd" / "anexo_rmd.xlsx"

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


def _baixa_anexo(anexo_id: int, url: str) -> Path:
    print(f"anexo RMD id={anexo_id} <- {url[:100]}", flush=True)
    content = get(url, timeout=180)
    XLSX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        nomes = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if not nomes:
            raise RuntimeError("ZIP sem XLSX")
        XLSX_CACHE.write_bytes(zf.read(nomes[0]))
    _salvar_id(anexo_id, url)
    meta_gravar(XLSX_CACHE, fonte="rmd/thot-anexo", url=url,
                identificador_publicacao=f"anexo:{anexo_id}")
    return XLSX_CACHE


def baixar(force: bool = False) -> Path:
    """baixar(): obtém a versão ATUAL do último anexo do RMD.

    O anexo muda de URL a cada publicação mensal, então a revalidação aqui
    é o identificador da publicação (id do anexo no thot): igual ao
    registrado nos metadados -> mantém a cópia local; id novo -> baixa o
    anexo novo. force=True transfere de novo mesmo assim.
    """
    meta = meta_ler(XLSX_CACHE)
    cache_ok = (XLSX_CACHE.exists() and XLSX_CACHE.stat().st_size > 0
                and meta is not None)
    try:
        if cache_ok and not force:
            anexo_id, url = descobrir_anexo()  # consulta leve: há publicação nova?
            if meta.get("identificador_publicacao") == f"anexo:{anexo_id}":
                return XLSX_CACHE  # mesma publicação
        else:
            anexo_id, url = descobrir_anexo()
    except RuntimeError as e:
        tem_copia = XLSX_CACHE.exists() and XLSX_CACHE.stat().st_size > 0
        if tem_copia:
            # fonte indisponível: NÃO se disfarça de sucesso — falha, mas
            # aponta a saída (a cópia local tem procedência registrada)
            origem = (f"{meta.get('identificador_publicacao')}, coletada em "
                      f"{meta.get('data_coleta')}" if meta
                      else "cópia de coleta antiga, sem metadados")
            raise RuntimeError(
                f"fonte do RMD indisponível: {e} — há cópia local ({origem}): "
                "use --cache para usá-la ou --force para tentar "
                "transferir de novo") from e
        raise
    return _baixa_anexo(anexo_id, url)


def usar_cache() -> Path:
    """usa_cache(): usa o XLSX já coletado, sem consultar a fonte.

    Integridade validada pelo hash_sha256 dos metadados.
    """
    return _usar_cache_arquivo("anexo_rmd.xlsx", "rmd")


# ----------------------------------------------------------------- parse helpers


def _acha_cabecalho_meses(bruto: pd.DataFrame) -> int:
    for i in range(min(15, len(bruto))):
        n = sum(
            1 for j in range(bruto.shape[1])
            if isinstance(bruto.iloc[i, j], str) and RE_MES.match(bruto.iloc[i, j].strip())
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
        if isinstance(cab.iloc[j], str) and RE_MES.match(cab.iloc[j].strip())
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
            m = RE_MES.match(cab.iloc[j].strip())
            if not m:
                continue
            ano = ano_de_dois_digitos(m.group(2))
            regs.append({
                "indicador": label,
                "data": pd.Timestamp(ano, MESES[m.group(1).lower()], 1) + pd.offsets.MonthEnd(0),
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
    if not frames:
        # nenhuma aba com o cabeçalho esperado: devolve o esquema vazio em
        # vez de estourar o pd.concat de lista vazia. O aviso importa: pode
        # ser zero legítimo, mas também mudança de layout da STN.
        print("aviso: nenhuma aba de custo médio reconhecida — salvando vazio")
        frames = [pd.DataFrame(columns=["indicador", "data", "valor", "tabela"])]
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns={"indicador": "escopo", "valor": "taxa_pct_aa"})
    df["unidade"] = "% a.a."
    return salvar_parquet(df, "rmd_custo_medio")


def processar_detentores_titulo() -> pd.DataFrame:
    """RMD 2.8 — estoque da DPMFi por detentor E por título (R$ bi e %).

    Cada bloco do anexo é um título (LFT, LTN, NTN-B, NTN-F, OUTROS); as
    colunas trazem pares (valor R$ bi, participação) por grupo de detentor.
    Responde "quem segura o quê" — o 2.7 só traz o total por grupo.
    """
    bruto = _ler("2.8")
    col0 = bruto.iloc[:, 0]
    # blocos: rótulos de título na coluna 0 (as datas 'mar/18*' têm '/')
    blocos = [(i, str(v).strip()) for i, v in col0.items()
              if isinstance(v, str) and v.strip() and "/" not in v]
    regs: list[dict] = []
    for bi, (ini, titulo) in enumerate(blocos):
        fim = blocos[bi + 1][0] if bi + 1 < len(blocos) else len(bruto)
        bloco = bruto.iloc[ini:fim]
        # cabeçalho: linha com 'Inst' na coluna de valor 1
        cab_i = next((j for j in range(len(bloco))
                      if isinstance(bloco.iloc[j, 1], str)
                      and "Inst" in bloco.iloc[j, 1]), None)
        if cab_i is None:
            continue
        cab = bloco.iloc[cab_i]
        # grupos nas colunas de valor (ímpares); a par é a participação
        grupos = [(j, str(cab.iloc[j]).strip()) for j in range(1, 17, 2)
                  if isinstance(cab.iloc[j], str) and cab.iloc[j].strip()]
        for k in range(cab_i + 1, len(bloco)):
            d = _data_mista(bloco.iloc[k, 0])
            if d is None:
                continue
            for j, nome in grupos:
                val = bloco.iloc[k, j]
                if pd.isna(val):
                    continue
                regs.append({
                    "titulo": titulo,
                    "detentor": nome,
                    "data": d,
                    "valor_bi": float(val),
                    "participacao": float(bloco.iloc[k, j + 1])
                    if not pd.isna(bloco.iloc[k, j + 1]) else float("nan"),
                })
    df = pd.DataFrame(regs)
    if df.empty:
        raise ValueError(
            "processar_detentores_titulo: nenhum registro — o layout do "
            "anexo 2.8 mudou?")
    if df.groupby(["titulo", "detentor"]).size().min() < 100:
        raise ValueError(
            "processar_detentores_titulo: série curta demais por grupo — "
            "a extração pode estar cortando blocos")
    return salvar_parquet(df, "rmd_detentores_titulo")


def _data_mista(v) -> "pd.Timestamp | None":
    """Data do anexo: datetime (1º ou fim de mês) ou rótulo 'mar/18*'
    (com asterisco de nota). Tudo normalizado para o FIM do mês."""
    if isinstance(v, (pd.Timestamp, date)) and not isinstance(v, str):
        try:
            return pd.Timestamp(v) + pd.offsets.MonthEnd(0)
        except (ValueError, TypeError):
            return None
    if isinstance(v, str):
        m = RE_MES.match(v.strip().rstrip("*"))
        if m:
            ano = ano_de_dois_digitos(m.group(2))
            return pd.Timestamp(ano, MESES[m.group(1).lower()], 1) \
                + pd.offsets.MonthEnd(0)
    return None


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


def main(force: bool = False, so_cache: bool = False) -> None:
    """CLI: default = baixar() (compara a publicação atual);
    --cache = usar_cache() (só cópia local, sem rede);
    --force = baixar(force=True) (transfere de novo)."""
    if so_cache:
        usar_cache()
    else:
        baixar(force=force)
    for fn in (processar_detentores, processar_detentores_titulo,
               processar_custo_medio, processar_composicao, processar_reserva):
        out = fn()
        n = len(pd.read_parquet(out)) if isinstance(out, Path) else len(out)
        print(f"{fn.__name__}: {n} linhas")


if __name__ == "__main__":
    import sys

    main(force="--force" in sys.argv, so_cache="--cache" in sys.argv)
