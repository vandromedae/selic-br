"""Discursos e apresentações do BCB — índice público via API interna do portal.

O portal (SPA Angular) não expõe listagem em HTML, mas a API interna é pública
e sem autenticação. Descoberta de engenharia reversa dos bundles JS:

- `GET /api/configAmbiente` .......... configuração base (SITE_ID)
- `GET /api/servico/sitebcb/{fonte}` . listagens "cronológicas" do portal
- `GET /api/servico/sitebcb/discursos?ano={YYYY}` .... discursos do ano
- `GET /api/servico/sitebcb/discursos/Anos` .......... datas de todos

Fonte identificada na página `/acessoinformacao/discursos`, que renderiza
`<bcb-cronologicos [fonte_dados]="'discursos'">`; o componente
`cronologico-lista` chama `getContentCloudServiceV2(fonte_dados)` →
`/api/servico/{siteId}/{fonte}` (chunk-GKG6G3VS.js).

Saídas:
- dados/processado/discursos_indice.csv ... id, ano, data, titulo, autor,
  url_pdf, tamanho, extensao (índice completo 2002–hoje)
- (com --foco) dados/bruto/discursos/*.pdf + texto/*.txt ... recorte

Recorte "foco" (transparência: é uma ESCOLHA documentada, não o corpus inteiro):
- ano ≥ 2021 (mesma janela das atas do Copom);
- tema monetário no título (Copom, Selic, juros, inflação, política monetária,
  cenários econômicos, expectativas, Relatório de Política Monetária);
- autoridade de decisão (Presidente/Diretor) ou divulgação de Relatório.

Rodar:
  python -m src.extratores.discursos            # só índice
  python -m src.extratores.discursos --foco     # baixa PDFs + texto
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from .base import BRUTO, PROCESSADO, _UA

API = "https://www.bcb.gov.br/api"
SITE = "sitebcb"
BRUTO_DISCURSOS = BRUTO / "discursos"
TEXTO_DIR = BRUTO_DISCURSOS / "texto"

MAX_ANO = 2026  # ano final da varredura (ajustar conforme avança o calendário)

# regexes do recorte "foco" (ver docstring)
_FOCO_TEMA = re.compile(
    r"Copom|Selic|juros|infla|pol[íi]tica monet|Relat[óo]rio de Pol"
    r"|Taylor|expectativ|cen[áa]rios econ", re.I)
_FOCO_AUTOR = re.compile(
    r"Presidente|Diretor|Relat[óo]rio de Pol|Divulga[çc][ãa]o", re.I)


def _get(url: str, params: dict | None = None, tentativas: int = 3,
         timeout: int = 60) -> dict | None:
    """GET com retry. Retorna dict ou None se a fonte não responder."""
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=_UA, timeout=timeout)
            if r.status_code == 200:
                # o endpoint de discursos às vezes devolve Latin-1
                for enc in ("utf-8", "latin-1", "cp1252"):
                    try:
                        return json.loads(r.content.decode(enc))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                return None
            if r.status_code in (404, 400, 500):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def _itens_por_ano(ano: int) -> list[dict]:
    d = _get(f"{API}/servico/{SITE}/discursos",
             params={"ano": ano, "ordem": "Title asc"})
    if not d:
        return []
    return d.get("conteudo") or []


def descobrir_anos() -> list[int]:
    """Anos com discursos: via /Anos (datas de referência) + varredura fina."""
    d = _get(f"{API}/servico/{SITE}/discursos/Anos")
    anos: set[int] = set()
    if d:
        for it in d.get("conteudo") or []:
            ref = (it.get("dataReferencia") or "")[:4]
            if ref.isdigit():
                anos.add(int(ref))
    if anos:
        # completa com anos intermediários vazios e o ano corrente
        lo, hi = min(anos), max(MAX_ANO, max(anos))
        anos |= set(range(lo, hi + 1))
    return sorted(anos)


def montar_indice(anos: list[int]) -> list[dict]:
    linhas: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_itens_por_ano, a): a for a in anos}
        for fut in as_completed(futs):
            ano = futs[fut]
            itens = fut.result()
            if not itens:
                print(f"  {ano}: 0 itens")
                continue
            for it in itens:
                url = it.get("Url") or (it.get("arquivo") or {}).get(
                    "ServerRelativeUrl") or ""
                data = (it.get("dataReferencia")
                        or it.get("DataPublicacao") or "")[:10]
                desc = re.sub(r"<[^>]+>", " ", it.get("descricao") or "")
                desc = re.sub(r"\s+", " ", desc).strip()
                linhas.append({
                    "id": it.get("Id"),
                    "ano": ano,
                    "data": data,
                    "titulo": (it.get("titulo") or "").strip(),
                    "autor": desc,
                    "url_pdf": url,
                    "tamanho": it.get("Tamanho"),
                })
            print(f"  {ano}: {len(itens)} itens")
    return sorted(linhas, key=lambda x: (x["data"], str(x["titulo"])))


def salvar_indice(linhas: list[dict]) -> Path:
    import pandas as pd

    df = pd.DataFrame(linhas).drop_duplicates(subset=["id", "url_pdf", "titulo"])
    destino = PROCESSADO / "discursos_indice.csv"
    df.to_csv(destino, index=False)
    print(f"ok: {destino} ({len(df)} discursos)")
    return destino


# ------------------------------------------------------------------ recorte foco


def recorte_foco() -> "pd.DataFrame":
    """Índice filtrado pelo recorte documentado na docstring (ano ≥ 2021)."""
    import pandas as pd

    df = pd.read_csv(PROCESSADO / "discursos_indice.csv")
    df = df[df.ano >= 2021].copy()
    tema = df.titulo.fillna("").str.contains(_FOCO_TEMA)
    autor = df.titulo.fillna("").str.contains(_FOCO_AUTOR)
    return df[tema & autor].reset_index(drop=True)


def _texto_pdf(caminho: Path) -> str:
    from pypdf import PdfReader

    # PDFs com content streams muito grandes (slides de divulgação) estouram o
    # orçamento padrão de parsing do pypdf (2M tokens) com LimitReachedError.
    try:
        from pypdf._configuration import overwrite_configuration
        overwrite_configuration(stream_parsing_work_maximum_count=50_000_000)
    except Exception:  # pypdf antigo sem a API de configuração
        pass
    reader = PdfReader(str(caminho))
    paginas = [re.sub(r"\s+", " ", (pg.extract_text() or "")).strip()
               for pg in reader.pages]
    return "\n".join(p for p in paginas if p)


def baixar_foco() -> Path:
    """Baixa os PDFs do recorte foco e extrai texto (cache: só baixa o ausente)."""
    foco = recorte_foco()
    BRUTO_DISCURSOS.mkdir(parents=True, exist_ok=True)
    TEXTO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"recorte foco: {len(foco)} discursos")

    def _um(row) -> tuple[int, str | None, int]:
        url = row.url_pdf
        if not isinstance(url, str) or not url:
            return (row.id, None, 0)
        ext = url.rsplit(".", 1)[-1].lower() if "." in url else "pdf"
        if ext not in ("pdf", "pps", "ppt"):  # só textuais
            return (row.id, None, 0)
        pdf = BRUTO_DISCURSOS / f"d_{row.id}.{ext}"
        if not pdf.exists():
            u = url if url.startswith("http") else f"https://www.bcb.gov.br{url}"
            try:
                r = requests.get(u, headers=_UA, timeout=120)
                if r.status_code != 200 or len(r.content) < 500:
                    return (row.id, None, 0)
                pdf.write_bytes(r.content)
                time.sleep(0.2)
            except requests.RequestException:
                return (row.id, None, 0)
        txt = TEXTO_DIR / f"d_{row.id}.txt"
        if not txt.exists() and ext == "pdf":
            try:
                txt.write_text(_texto_pdf(pdf), encoding="utf-8")
            except Exception as e:  # PDF protegido/corrompido
                print(f"  ! id {row.id}: falha ao extrair ({type(e).__name__})")
                return (row.id, None, 0)
        n = len(txt.read_text(encoding="utf-8")) if txt.exists() else 0
        return (row.id, str(pdf.relative_to(BRUTO)), n)

    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fid, arq, n in ex.map(_um, foco.itertuples()):
            if arq and n:
                ok += 1
            else:
                print(f"  ! id {fid}: sem texto")
    print(f"extraídos: {ok}/{len(foco)}")
    return TEXTO_DIR


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    BRUTO_DISCURSOS.mkdir(parents=True, exist_ok=True)
    if "--foco" in argv:
        baixar_foco()
        return
    anos = descobrir_anos()
    print(f"anos: {anos[0]}–{anos[-1]} ({len(anos)} varreduras)")
    linhas = montar_indice(anos)
    salvar_indice(linhas)


if __name__ == "__main__":
    sys.exit(main())
