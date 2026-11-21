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
from ..config import FOCO_AUTOR, FOCO_TEMA, MAX_ANO

API = "https://www.bcb.gov.br/api"
SITE = "sitebcb"
BRUTO_DISCURSOS = BRUTO / "discursos"
TEXTO_DIR = BRUTO_DISCURSOS / "texto"

# FOCO_TEMA, FOCO_AUTOR (recorte "foco") e MAX_ANO vêm de src/config.py


class FalhaAPI(Exception):
    """A fonte não respondeu (status de erro, rede ou JSON inválido).

    Diferente de "ok, sem dados" (200 + lista vazia): a API do portal
    responde 200 com `conteudo: []` para anos sem discursos (testado:
    1995, 2050) — então qualquer status !=200 É falha, nunca falta de
    dado. Tratar falha como ausência de dado fazia montar_indice() rodar
    sem o ano e salvar_indice() sobrescrever o CSV sem ele.
    """


def _get(url: str, params: dict | None = None, tentativas: int = 3,
         timeout: int = 60) -> dict:
    """GET com retry. Retorna o JSON (dict) ou levanta FalhaAPI.

    Nunca retorna None: falha é exceção, "sem dados" é 200 + lista vazia.
    """
    ultimo = "?"
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
                raise FalhaAPI(f"HTTP 200 mas corpo não é JSON válido: {url}")
            if r.status_code in (404, 400):  # definitivo: retry não resolve
                raise FalhaAPI(f"HTTP {r.status_code}: {url}")
            ultimo = f"HTTP {r.status_code}"  # 500/502/429…: transitório
        except requests.RequestException as e:
            ultimo = type(e).__name__
        time.sleep(1.5 * (i + 1))
    raise FalhaAPI(
        f"sem resposta após {tentativas} tentativas ({ultimo}) — {url}"
        + (f" params={params}" if params else ""))


def _itens_por_ano(ano: int) -> list[dict]:
    d = _get(f"{API}/servico/{SITE}/discursos",
             params={"ano": ano, "ordem": "Title asc"})
    # falha propaga FalhaAPI; 200 sem itens -> [] legítimo
    return d.get("conteudo") or []


def descobrir_anos() -> list[int]:
    """Anos com discursos: via /Anos (datas de referência) + varredura fina."""
    d = _get(f"{API}/servico/{SITE}/discursos/Anos")
    anos: set[int] = set()
    for it in d.get("conteudo") or []:
        ref = (it.get("dataReferencia") or "")[:4]
        if ref.isdigit():
            anos.add(int(ref))
    if anos:
        # completa com anos intermediários vazios e o ano corrente
        lo, hi = min(anos), max(MAX_ANO, max(anos))
        anos |= set(range(lo, hi + 1))
    return sorted(anos)


def montar_indice(anos: list[int]) -> tuple[list[dict], list[int]]:
    """Coleta o índice. Retorna (linhas, anos_com_falha).

    Falha de requisição num ano não derruba os demais, mas também não é
    silenciosamente tratada como "ano sem discursos" (fail-closed: vira
    exit 1 em main, sem salvar).
    """
    linhas: list[dict] = []
    falhas: list[int] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_itens_por_ano, a): a for a in anos}
        for fut in as_completed(futs):
            ano = futs[fut]
            try:
                itens = fut.result()
            except FalhaAPI as e:
                falhas.append(ano)
                print(f"  {ano}: FALHA (requisição) — {e}")
                continue
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
    linhas.sort(key=lambda x: (x["data"], str(x["titulo"])))
    return linhas, sorted(falhas)


def salvar_indice(linhas: list[dict]) -> Path:
    import pandas as pd

    if not linhas:
        # fail-closed: lista vazia nunca sobrescreve o índice já salvo
        raise ValueError(
            "nenhuma linha para salvar — recusando sobrescrever "
            f"{PROCESSADO / 'discursos_indice.csv'}")
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
    tema = df.titulo.fillna("").str.contains(FOCO_TEMA)
    autor = df.titulo.fillna("").str.contains(FOCO_AUTOR)
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
    # slides (PPT→PDF) PERDEM conteúdo no extraction_mode="layout" (medido:
    # −25% dos chars nos 46 discursos, ex. d_1685: 30k → 16k) — aqui fica o
    # modo padrão; a correção de quebra de palavras é para as atas (copom.py)
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
        if ext != "pdf":
            # só PDF tem extração de texto no pipeline (ppt/pps do BCB seriam
            # baixados e nunca virariam .txt — nada de arquivo órfão)
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
        if not txt.exists():
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    BRUTO_DISCURSOS.mkdir(parents=True, exist_ok=True)
    if "--foco" in argv:
        baixar_foco()
        return 0
    try:
        anos = descobrir_anos()
    except FalhaAPI as e:
        print(f"falha na API de anos: {e}")
        return 1
    if not anos:
        print("falha: /Anos não retornou nenhum ano")
        return 1
    print(f"anos: {anos[0]}–{anos[-1]} ({len(anos)} varreduras)")
    linhas, falhas = montar_indice(anos)
    if falhas:
        print(f"falha de requisição em {len(falhas)} ano(s): {falhas}")
        print("índice NÃO salvo (fail-closed): falha de requisição não é "
              "falta de dados — rode de novo.")
        return 1
    if not linhas:
        print("nenhum item coletado; índice NÃO salvo")
        return 1
    salvar_indice(linhas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
