"""Discursos do BCB — índice de temas e trechos citáveis (fase de documentos).

Entrada:
- `dados/bruto/discursos/texto/d_{id}.txt` (recorte "foco", ver docstring de
  `src/extratores/discursos.py`: ano ≥ 2021 + tema monetário + autoridade)
- `dados/processado/discursos_indice.csv` (índice completo 2002–hoje)

Reaproveita `TEMAS` de `atas_copom` — a MESMA régua de indexação, para que
dê para comparar discursos × atas sem tradução entre vocabulários. É um
INVENTÁRIO de trechos citáveis, não NLP: cada trecho é a frase com a
expressão ±1 frase, sempre com autor, data e título para citação direta.

O que este módulo NÃO é: classificação de intenção. Um discurso conter a
expressão "juro real" não significa defesa de patamar — o trecho serve
para leitura humana.

Saídas:
- `temas()` ............ matriz discurso × tema (nº de frases)
- `trechos(tema)` ...... DataFrame (id, data, ano, autor, tema, trecho)
- `por_autor()` ........ quem fala de quê (frases por autor × tema)
- `salvar_trechos()` ... parquet `discursos_trechos` (dados/processado)

Rodar do repo root: PYTHONPATH=. python -m src.processa.discursos
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..extratores.base import RAIZ, salvar_parquet
from .atas_copom import TEMAS  # mesma régua das atas do Copom

TEXTO_DIR = RAIZ / "dados" / "bruto" / "discursos" / "texto"
INDICE = RAIZ / "dados" / "processado" / "discursos_indice.csv"

# nome do autor no TÍTULO (o campo `autor` do índice mistura nome e cidade):
# 1) "Apresentação do Diretor ..., NOME, na ..." (a maioria)
# 2) "Apresentação do Presidente NOME no evento ..." (sem vírgula)
_NOME_1 = re.compile(
    r"(?:Apresenta[çc][ãa]o|Discurso|Entrevista)[^.]{0,120}?,\s*"
    r"([A-ZÀ-Þ][\wÀ-ÿ]+(?: [A-ZÀ-Þ][\wÀ-ÿ]+){1,3}),")
_NOME_2 = re.compile(
    r"(?:do|da)\s+(?:Presidente|Diretor[a]?)\s+"
    r"([A-ZÀ-Þ][\wÀ-ÿ]+(?: [A-ZÀ-Þ][\wÀ-ÿ]+){1,3})\s+(?:no|na|em|para|sob)")

_FRASE = re.compile(r"[^.!?]+[.!?]")


def nome_de(titulo: str) -> str:
    """Nome do autor extraído do título; '?' se o padrão não casar."""
    m = _NOME_1.search(titulo) or _NOME_2.search(titulo)
    return m.group(1) if m else "?"


# ------------------------------------------------------------------ carregamento


def carrega_catalogo() -> pd.DataFrame:
    """Índice do recorte foco (só discursos com texto extraído).

    Colunas: id, data, ano, titulo, autor (nome limpo do título), url_pdf.
    """
    df = pd.read_csv(INDICE)
    df = df[df.ano >= 2021].copy()
    df = df[df.url_pdf.notna()].copy()
    # só o que tem texto na prateleira (recorte foco baixado)
    tem_texto = df.id.map(lambda i: (TEXTO_DIR / f"d_{int(i)}.txt").exists())
    df = df[tem_texto].copy()
    df["autor"] = df.titulo.fillna("").map(nome_de)
    return df.sort_values("data").reset_index(drop=True)


@lru_cache(maxsize=None)
def _texto(id_: int) -> str:
    p = TEXTO_DIR / f"d_{id_}.txt"
    if not p.exists():
        raise FileNotFoundError(f"{p} — rode src.extratores.discursos --foco")
    return p.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def _frases(id_: int) -> tuple[str, ...]:
    bruto = _FRASE.findall(_texto(id_))
    return tuple(f.strip() for f in bruto if len(f.split()) >= 4)


# ------------------------------------------------------------------ trechos / temas


def trechos(tema: str, contexto: int = 1) -> pd.DataFrame:
    """DataFrame (id, data, ano, autor, titulo, pos, tema, trecho) p/ um tema.

    O trecho é a frase com a expressão ± `contexto` frases adjacentes —
    o suficiente para ler sem sair do discurso original (citável).
    """
    if tema not in TEMAS:
        raise KeyError(f"tema '{tema}' não está em TEMAS")
    pat = re.compile(TEMAS[tema], re.IGNORECASE)
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        fs = _frases(int(row.id))
        for i, f in enumerate(fs):
            if pat.search(f):
                janela = " ".join(fs[max(0, i - contexto): i + contexto + 1])
                linhas.append({
                    "id": int(row.id), "data": row.data, "ano": int(row.ano),
                    "autor": row.autor, "titulo": row.titulo,
                    "pos": i, "tema": tema, "trecho": janela.strip(),
                })
    return pd.DataFrame(linhas, columns=[
        "id", "data", "ano", "autor", "titulo", "pos", "tema", "trecho"])


def temas() -> pd.DataFrame:
    """Matriz discursos × temas: nº de frases em que cada regex aparece.

    Contagem por frase (não por ocorrência múltipla dentro da frase), a
    mesma régua de `atas_copom.temas()`.
    """
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        fs = _frases(int(row.id))
        for tema, pat_str in TEMAS.items():
            pat = re.compile(pat_str, re.IGNORECASE)
            n = sum(bool(pat.search(f)) for f in fs)
            if n:
                linhas.append({"id": int(row.id), "data": row.data,
                               "ano": int(row.ano), "autor": row.autor,
                               "tema": tema, "n_frases": n})
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    return df.pivot_table(index=["id", "data", "ano", "autor"], columns="tema",
                          values="n_frases", fill_value=0).reset_index()


def por_autor() -> pd.DataFrame:
    """Frases por autor × tema — quem fala de quê no recorte foco."""
    mat = temas()
    if mat.empty:
        return mat
    cols = [c for c in TEMAS if c in mat.columns]
    g = mat.groupby("autor")[cols].sum().reset_index()
    g["total"] = g[cols].sum(axis=1)
    return g.sort_values("total", ascending=False).reset_index(drop=True)


def salvar_trechos() -> Path:
    blocos = [trechos(t) for t in TEMAS]
    df = pd.concat([b for b in blocos if not b.empty], ignore_index=True)
    df = df.sort_values(["id", "tema", "pos"]).reset_index(drop=True)
    return salvar_parquet(df, "discursos_trechos")


# ------------------------------------------------------------------ CLI


def main() -> None:
    cat = carrega_catalogo()
    print(f"foco com texto: {len(cat)} discursos "
          f"({cat.ano.min()}–{cat.ano.max()}), autores: {cat.autor.nunique()}")
    sem = (cat.autor == "?").sum()
    if sem:
        print(f"atenção: {sem} título(s) sem nome extraído")

    mat = temas()
    if not mat.empty:
        cols = [c for c in TEMAS if c in mat.columns]
        ausentes = [c for c in TEMAS if c not in mat.columns]
        resumo = mat.groupby("ano")[cols].sum()
        print("\n== matriz resumo (ano × tema, nº de frases) ==")
        print(resumo.to_string())
        if ausentes:
            print("\ntemas sem nenhuma ocorrência no corpus:", ausentes)

    a = por_autor()
    if not a.empty:
        print("\n== frases por autor (top) ==")
        print(a.head(12).to_string(index=False))

    p = salvar_trechos()
    print("\nok:", p)


if __name__ == "__main__":
    main()
