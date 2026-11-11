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
- `ruidos()` ........... trechos com cara de tabela/slide → CSV p/ revisão
- `formatos()` ......... slide vs prosa por discurso → CSV p/ revisão

Ruídos e formato NÃO entram na análise de temas: são um "aviso de ruído"
para leitura humana (o usuário pediu a lista para verificar). A régua de
ruído é `dens = 1 − letras/caracteres_sem_espaço > 0,40` (calibrada nos
912 trechos: 0,40→44/25, 0,45→19/11, 0,50→10/8); a de slide é título
com "Apresentação" OU ≥3 "Fonte:" OU ≥10 marcadores `•▪●·–-`
(calibrada: 45 de 46 slides, só id 1262 é prosa).

Rodar do repo root: PYTHONPATH=. python -m src.processa.discursos
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..extratores.base import RAIZ, ler_parquet, salvar_parquet
from .atas_copom import TEMAS  # mesma régua das atas do Copom

TEXTO_DIR = RAIZ / "dados" / "bruto" / "discursos" / "texto"
INDICE = RAIZ / "dados" / "processado" / "discursos_indice.csv"
PROC_DIR = RAIZ / "dados" / "processado"
LIMIAR_RUIDO = 0.40

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


# ------------------------------------------------------------------ ruídos / formato


def densidade(trecho: str) -> float:
    """1 − (letras / caracteres não-espaço): números e tabelas sobem a densidade.

    Prosa em português fica em ~0,30; trecho de tabela/slide passa de 0,40.
    (Espaços não contam no denominador — calibrado em 912 trechos:
    0,40→44 trechos/25 discursos, 0,45→19/11, 0,50→10/8.)
    """
    if not trecho:
        return 1.0
    alvo = [c for c in trecho if not c.isspace()]
    if not alvo:
        return 1.0
    letras = sum(c.isalpha() for c in alvo)
    return 1.0 - letras / len(alvo)


def ruidos(limiar: float = LIMIAR_RUIDO) -> pd.DataFrame:
    """Trechos do inventário com cara de tabela/slide (dens > limiar).

    Colunas: id, data, autor, tema, pos, densidade, trecho, url — a lista
    que o usuário pediu para conferir manualmente. Salva em
    `dados/processado/discursos_ruidos.csv`.
    """
    df = ler_parquet("discursos_trechos")
    cat = carrega_catalogo()[["id", "url_pdf"]].rename(
        columns={"url_pdf": "url"})
    df = df.merge(cat, on="id", how="left")
    df["densidade"] = df.trecho.map(densidade)
    df = (df[df.densidade > limiar]
          .sort_values("densidade", ascending=False)
          .reset_index(drop=True))
    return df[["id", "data", "autor", "tema", "pos", "densidade",
               "trecho", "url"]]


_FONTE = re.compile(r"\bFonte\s*:", re.IGNORECASE)
_MARCADORES = "•▪●·–-"


def formatos() -> pd.DataFrame:
    """Slide vs prosa por discurso — o PDF é apresentação ou texto corrido?

    É slide se: o título começa com "Apresentação" OU o texto tem ≥3
    "Fonte:" OU ≥10 marcadores de lista (`•▪●·–-`, contados em qualquer
    lugar do texto — a extração do PDF cola marcadores no meio da linha).
    Motivo fica na coluna `motivo` para conferência. Salva em
    `dados/processado/discursos_formato.csv`.
    """
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        texto = _texto(int(row.id))
        motivos = []
        if str(row.titulo).strip().lower().startswith("apresenta"):
            motivos.append("titulo_apresentacao")
        n_fonte = len(_FONTE.findall(texto))
        if n_fonte >= 3:
            motivos.append(f"fontes_{n_fonte}")
        n_bullets = sum(texto.count(c) for c in _MARCADORES)
        if n_bullets >= 10:
            motivos.append(f"bullets_{n_bullets}")
        linhas.append({
            "id": int(row.id), "data": row.data, "autor": row.autor,
            "titulo": row.titulo,
            "formato": "slide" if motivos else "prosa",
            "motivo": ";".join(motivos) or "-",
        })
    return pd.DataFrame(linhas)


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

    # -- ruídos (tabelas/slides no meio dos trechos) e formato dos PDFs --
    r = ruidos()
    arq_r = PROC_DIR / "discursos_ruidos.csv"
    r.to_csv(arq_r, index=False, encoding="utf-8")
    print(f"\n== ruídos (densidade > {LIMIAR_RUIDO}): "
          f"{len(r)} trechos em {r.id.nunique()} discursos ==")
    print("ok:", arq_r)

    f = formatos()
    arq_f = PROC_DIR / "discursos_formato.csv"
    f.to_csv(arq_f, index=False, encoding="utf-8")
    n_slides = (f.formato == "slide").sum()
    prosa = f[f.formato == "prosa"]
    print(f"\n== formato dos {len(f)} discursos: "
          f"{n_slides} slides / {len(prosa)} prosa ==")
    if not prosa.empty:
        print(prosa[["id", "data", "autor", "titulo"]]
              .to_string(index=False))
    print("ok:", arq_f)


if __name__ == "__main__":
    main()
