"""Atas do Copom (BCB) — descoberta por probe, download e extração de texto.

As atas são PDFs públicos com nome padronizado:
    https://www.bcb.gov.br/content/copom/atascopom/Copom{num}-not{yyyymmdd}{num}.pdf

Não existe API pública estável listando os pares (número, data) — o portal
vorto SPA. A descoberta aqui valida pares candidatos por requisição HTTP
(200 = par válido) usando o calendário de reuniões do Copom, que desde ~2000
tem 8 reuniões anuais com datas quase idênticas ano a ano
(~28/1, ~18/3, ~29/4, ~17/6, ~5/8, ~16/9, ~4/11, ~9/12 — 2º dia).

Base confirmada por download: nº 232 = 2020-05-06 (ª 230ª reunião).

Saídas (cache):
- dados/bruto/copom/indice.json .......... pares (num, data) validados
- dados/bruto/copom/ata_{num}.pdf ........ PDF da ata
- dados/processado/copom_atas.csv ........ catálogo: num, data, ano, arquivo, n_caracteres
- dados/bruto/copom/texto/ata_{num}.txt ... texto integral extraído

Rodar: python -m src.extratores.copom
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import requests

from .base import BRUTO, PROCESSADO

URL_ATAS = "https://www.bcb.gov.br/content/copom/atascopom"

# agendamento padrão (2º dia da reunião), por posição
DIAS_PADRAO = [(28, 1), (18, 3), (29, 4), (17, 6), (5, 8), (16, 9), (4, 11), (9, 12)]
JITTER_DIAS = 3

# nº 229? = 2020-05-06 confirmado; reuniões ~8/ano a partir daí
NUM_BASE, DATA_BASE = 230, date(2020, 5, 6)

BRUTO_COPOM = BRUTO / "copom"
INDICE = BRUTO_COPOM / "indice.json"

UA = {"User-Agent": "Mozilla/5.0 (juros-e-divida; pesquisa de transparencia)"}


# ------------------------------------------------------------------ candidates


def _datas_candidatas(ano: int) -> list[date]:
    out = []
    for dia, mes in DIAS_PADRAO:
        base = date(ano, mes, dia)
        for off in range(-JITTER_DIAS, JITTER_DIAS + 1):
            d = base + timedelta(days=off)
            if d.year == ano:
                out.append(d)
    return sorted(set(out))


def _numeros_candidatos(ano: int) -> list[int]:
    """Nºs esperados: 8 reuniões/ano, sequenciais a partir de 2021 (2020 terminou
    na 235ª reunião — nº 229=18/3, 230=6/5, …, 235=9/12/2020: confirmado por
    download direto e pela tabela pública do fulljoin)."""
    inicio = {2021: 236}
    for y in range(2022, 2027):
        inicio[y] = inicio[y - 1] + 8
    if ano not in inicio:
        return []
    return list(range(inicio[ano], inicio[ano] + 8))


def _url_para(num: int, d: date, maiusculo: bool = False) -> str:
    nome = f"Copom{num}-not{d:%Y%m%d}{num}.pdf"
    if maiusculo:
        nome = nome.replace("Copom", "COPOM")
    return f"{URL_ATAS}/{nome}"


def _checa_url(url: str, timeout: int = 20) -> bool:
    try:
        r = requests.head(url, headers=UA, timeout=timeout, allow_redirects=False)
        if r.status_code == 200:
            return True
        # alguns CDNs recusam HEAD — dupla-checa com GET varião
        if r.status_code in (403, 405):
            g = requests.get(url, headers=UA, timeout=timeout, stream=True)
            ok = g.status_code == 200
            g.close()
            return ok
        return False
    except requests.RequestException:
        return False


def _janela(base: date, r: int) -> list[date]:
    return [base + timedelta(days=o) for o in range(-r, r + 1)]


def _candidatas_faltantes(pares: dict[int, str], nums_ano: list[int]) -> list[tuple[int, date]]:
    """Datas candidatas p/ números faltantes, interpolando/extrapolando entre
    pares já confirmados (o espaçamento Copom é estável: ~45-52 dias)."""
    out = []
    for n in nums_ano:
        if n in pares:
            continue
        prev = [k for k in pares if k < n]
        nxt = [k for k in pares if k > n]
        cand: set[date] = set()
        if prev and nxt:
            k0, k1 = max(prev), min(nxt)
            d0, d1 = date.fromisoformat(pares[k0]), date.fromisoformat(pares[k1])
            base = d0 + (d1 - d0) * (n - k0) / (k1 - k0)
            cand |= set(_janela(base, 12))  # janela larga: datas fora do padrão (ex. nº 236 em 20/1/2021)
        if prev:  # extrapola para trás com o passo médio dos vizinhos
            k0 = max(prev)
            seguintes = [k for k in pares if k > k0]
            if seguintes:
                k1 = min(seguintes)
                d0, d1 = date.fromisoformat(pares[k0]), date.fromisoformat(pares[k1])
                passo = (d1 - d0) / max(k1 - k0, 1)
                base = d0 - passo * (k0 - n)
                cand |= set(_janela(base, 9))
        if nxt:  # extrapola para frente (nº além do último confirmado)
            k1 = min(nxt)
            anteriores = [k for k in pares if k < k1]
            if anteriores:
                k0 = max(anteriores)
                d0, d1 = date.fromisoformat(pares[k0]), date.fromisoformat(pares[k1])
                passo = (d1 - d0) / max(k1 - k0, 1)
                base = d1 + passo * (n - k1)
                cand |= set(_janela(base, 9))
            else:  # sem anteriores: passo médio observado entre reuniões (~50 dias)
                base = date.fromisoformat(pares[k1]) - timedelta(days=50 * (k1 - n))
                cand |= set(_janela(base, 10))
        for d in cand:
            if pares.get(n) != d.isoformat():
                out.append((n, d))
    return out


def descobrir(ano_inicio: int = 2021, ano_fim: int = 2026) -> dict[int, str]:
    """Valida pares (num, data) e retorna {num: 'YYYY-MM-DD'}."""
    BRUTO_COPOM.mkdir(parents=True, exist_ok=True)
    pares: dict[int, str] = {}
    if INDICE.exists():
        pares = {int(k): v for k, v in json.loads(INDICE.read_text()).items()}

    jobs = []
    for ano in range(ano_inicio, ano_fim + 1):
        datas = _datas_candidatas(ano)
        nums = _numeros_candidatos(ano)
        # faltantes: varre TODAS as datas do ano (mais robusto que janela estreita)
        falt = [n for n in nums if n not in pares]
        for num in nums:
            for d in datas:
                ja_feito = pares.get(num) == d.isoformat()
                jobs.append((num, d, ja_feito))
        # folga numérica: se o ano não fechou 8, tenta nº vizinhos (-2..+2)
        if 0 < len([n for n in nums if n in pares]) < 8:
            for viz in [-2, -1, 1, 2]:
                extra = [max(nums[0] + viz, 236)]
                for nx in extra:
                    if nx not in nums:
                        for d in datas:
                            jobs.append((nx, d, pares.get(nx) == d.isoformat()))

    def _varredura(num: int, d: date, ja: bool) -> tuple[int, date] | None:
        if ja:
            return None
        if _checa_url(_url_para(num, d)):
            return (num, d)
        return None

    pendentes = [j for j in jobs if not j[2]]
    # segunda rodada: interpolação/extrapolação entre pares já confirmados
    por_ano_nums: dict[int, list[int]] = {}
    for ano in range(ano_inicio, ano_fim + 1):
        por_ano_nums[ano] = _numeros_candidatos(ano)
    for ano, nums in por_ano_nums.items():
        pendentes += [(n, d, False) for (n, d)
                      in _candidatas_faltantes(pares, nums)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(_varredura, *j): j for j in pendentes}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                pares[res[0]] = res[1].isoformat()

    INDICE.write_text(json.dumps({str(k): v for k, v in sorted(pares.items())}, indent=1,
                                 ensure_ascii=False))
    return pares


# ------------------------------------------------------------------ download + texto


def _texto_pdf(caminho: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(caminho)
    paginas = []
    for pg in reader.pages:
        t = pg.extract_text() or ""
        paginas.append(re.sub(r"\s+", " ", t).strip())
    return "\n".join(p for p in paginas if p)


def baixar_e_extrair(pares: dict[int, str]) -> list[dict]:
    tex_dir = BRUTO_COPOM / "texto"
    tex_dir.mkdir(parents=True, exist_ok=True)
    catalogo = []
    for num, iso in sorted(pares.items()):
        pdf_path = BRUTO_COPOM / f"ata_{num}.pdf"
        if not pdf_path.exists():
            ano, mes, dia = (int(x) for x in iso.split("-"))
            url = _url_para(num, date(ano, mes, dia))
            try:
                r = requests.get(url, headers=UA, timeout=60)
                if r.status_code != 200 and "/Copom" in url:
                    r = requests.get(url.replace("/Copom", "/COPOM"), headers=UA, timeout=60)
                r.raise_for_status()
                pdf_path.write_bytes(r.content)
            except requests.RequestException as e:
                print(f"  ! ns{num}: falha ao baixar ({e})")
                continue
        txt = tex_dir / f"ata_{num}.txt"
        try:
            if not txt.exists():
                txt.write_text(_texto_pdf(pdf_path), encoding="utf-8")
            n_chars = len(txt.read_text(encoding="utf-8"))
        except Exception as e:  # PDF truncado / corrompido
            print(f"  ! ns{num}: falha ao extrair texto ({e})")
            continue
        catalogo.append({
            "num": num, "data": iso, "ano": int(iso[:4]),
            "arquivo": str(pdf_path.relative_to(BRUTO)),
            "texto": f"copom/texto/ata_{num}.txt",
            "n_caracteres": n_chars,
        })
    return catalogo


def catalogo_csv(catalogo: list[dict]) -> None:
    import pandas as pd

    df = pd.DataFrame(catalogo).sort_values("num").reset_index(drop=True)
    destino = PROCESSADO / "copom_atas.csv"
    df.to_csv(destino, index=False)
    print("ok:", destino)


# ------------------------------------------------------------------ CLI


def main() -> None:
    pares = descobrir(2021, 2026)
    print(f"pares válidos: {len(pares)} (nº {min(pares)} … {max(pares)})")
    por_ano: dict[int, list[int]] = {}
    for num, iso in pares.items():
        por_ano.setdefault(int(iso[:4]), []).append(num)
    for ano, nums in sorted(por_ano.items()):
        print(f"  {ano}: {len(nums)} atas ({min(nums)}–{max(nums)})")
    catalogo = baixar_e_extrair(pares)
    catalogo_csv(catalogo)


if __name__ == "__main__":
    sys.exit(main())
