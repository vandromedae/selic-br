"""Atas do Copom — índice de temas e extração de trechos citáveis.

Entrada: `dados/bruto/copom/texto/ata_{num}.txt` + catálogo
`dados/processado/copom_atas.csv` (produzido por `src/extratores/copom.py`).

O que este módulo NÃO é: análise semântica automatizada. É um INVENTÁRIO
de onde surgem trechos para leitura humana (fase de documentos, tudo
citável com ata + data — nomes individuais não são públicos).

Saídas:
- `temas()` ............ matriz ata × tema com nº de ocorrências
- `trechos(tema)` ...... DataFrame (num, data, tema, trecho) — trecho =
  frase(s) com a expressão, ±1 frase de contexto
- `decisoes()` ......... ata ↔ Selic meta resultante (SGS 432)
- `salvar_trechos()` ... parquet `copom_trechos` (dados/processado)

Rodar do repo root: PYTHONPATH=. python -m src.processa.atas_copom
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..extratores.base import RAIZ, ler_parquet, salvar_parquet

TEXTO_DIR = RAIZ / "dados" / "bruto" / "copom" / "texto"

# ------------------------------------------------------------------ temas
# Regexes por expressão literal (não exaustivas): servem para localizar
# FRASES candidatas em cada ata. Palavras isoladas demais (= "fiscal")
# poluiriam o índice; cada alternativa tem ao menos duas palavras de âncora.

TEMAS: dict[str, str] = {
    "juro real": (
        r"juros? reais?\b|juro real"
        r"|aperto monetário em termos reais"
        r"|taxa real de juros?|juros? real neutra"
    ),
    "juro real ex ante": r"\bex[- ]ante\b",
    "risco fiscal": (
        r"ris[ck]os? fiscais?"
        r"|domin[âa]ncia fiscal|sustentabilidade fiscal"
        r"|incertezas? fiscal(?:is)?|deteriora[çc][ãa]o fiscal|impasse fiscal"
        r"|pol[íi]tica fiscal|estrat[ée]gia fiscal|quadro fiscal|lado fiscal"
        r"|d[ée]ficit p[úu]blico|d[íi]vida p[úu]blica (l[íi]quida?|bruta)?"
        r"|fracasso fiscal|contas p[úu]blicas|despesa(s)? (p[úu]blica[s]?|obrigat)"
    ),
    "credibilidade": r"credib\w*|desancorad\w*|ancorad\w*",
    "histórico de desencontro": (
        r"desencontro\w*"
        r"|(sequência|recorrência) de surpresas"
        r"|surpresas? altistas|virada[s]? (inesperadas? )?na inflação"
        r"|hist[óo]ricamente (alto|baixo|elevad|intens|importante)"
    ),
    "surpresa inflacionária": (
        r"surpresas? infl"
        r"|acima do esperado|vieram acima|veio acima"
        r"|diferentes do esperado|desconfirm\w*"
    ),
    "câmbio": r"c[âa]mbi\w*",
    # nota: "swap" NÃO aparece em nenhuma das 46 atas 2021–2026 (verificado);
    # tema removido do índice — o derivativo cambial não é citado nos textos.
    "meta de inflação": (
        r"regime de metas|metas? de infla[çc][ãa]o\b"
        r"|meta para a inflação|redor da meta|cumprimento da meta"
        r"|converg[êe]ncia da inflação para as metas|metas fixadas"
    ),
    "mercado financeiro": (
        r"curvas? de juros?"
        r"|derivativos|mercado (de futuros|de derivativos|financeiro)"
        r"|pre[çc]os de (ativos|op[çc][õo]es|swaps)"
        r"|contratos (futuros|a termo)|prêmio \w* de risco"
        r"|Focus\b"
    ),
    "risco externo": (
        r"(cen[áa]rio|economia|condi[çc][õo]es) (internacional|global|externo)"
        r"|guerra\b|ucr[âa]nia|pandemi\w*|tarifa(ços)?|guerras? comercial(?:is)?"
    ),
}

_FRASE = re.compile(r"[^.!?]+[.!?]")


# ------------------------------------------------------------------ carregamento


def carrega_catalogo() -> pd.DataFrame:
    c = pd.read_csv(RAIZ / "dados" / "processado" / "copom_atas.csv")
    return c.sort_values("num").reset_index(drop=True)


@lru_cache(maxsize=None)
def _texto(num: int) -> str:
    p = TEXTO_DIR / f"ata_{num}.txt"
    if not p.exists():
        raise FileNotFoundError(f"{p} — rode src.extratores.copom")
    return p.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def _frases(num: int) -> tuple[str, ...]:
    bruto = _FRASE.findall(_texto(num))
    return tuple(f.strip() for f in bruto if len(f.split()) >= 4)


def carrega_atas() -> pd.DataFrame:
    """Catalogo + nº de frases (num, data, ano, num, n_frases)."""
    cat = carrega_catalogo()
    cat["n_frases"] = cat.num.astype(int).map(lambda n: len(_frases(int(n))))
    return cat


# ------------------------------------------------------------------ trechos


def trechos(tema: str, contexto: int = 1) -> pd.DataFrame:
    """DataFrame (num, data, ano, pos_ata, tema, trecho) para um tema de TEMAS.

    O trecho é a frase com a expressão ± `contexto` frases adjacentes,
    o suficiente para leitura sem sair da ata original (página citável).
    """
    if tema not in TEMAS:
        raise KeyError(f"tema '{tema}' não está em TEMAS")
    pat = re.compile(TEMAS[tema], re.IGNORECASE)
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        fs = _frases(int(row.num))
        for i, f in enumerate(fs):
            if pat.search(f):
                janela = " ".join(fs[max(0, i - contexto): i + contexto + 1])
                linhas.append({
                    "num": int(row.num), "data": row.data, "ano": int(row.ano),
                    "pos_ata": i, "tema": tema, "trecho": janela.strip(),
                })
    return pd.DataFrame(linhas, columns=["num", "data", "ano", "pos_ata", "tema", "trecho"])


def temas() -> pd.DataFrame:
    """Matriz atas × temas: nº de frases por ata em que cada regex aparece.

    Contagem é por frase (não por ocorrência múltipl dentro da frase)
    para evitar que uma enumeração longa estufe um único trecho.
    """
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        fs = _frases(int(row.num))
        for tema, pat_str in TEMAS.items():
            pat = re.compile(pat_str, re.IGNORECASE)
            n = sum(bool(pat.search(f)) for f in fs)
            if n:
                linhas.append({"num": int(row.num), "data": row.data,
                               "ano": int(row.ano), "tema": tema, "n_frases": n})
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    return df.pivot_table(index=["num", "data", "ano"], columns="tema",
                          values="n_frases", fill_value=0).reset_index()


def salvar_trechos() -> Path:
    blocos = [trechos(t) for t in TEMAS]
    df = pd.concat([b for b in blocos if not b.empty], ignore_index=True)
    df = df.sort_values(["num", "tema", "pos_ata"]).reset_index(drop=True)
    return salvar_parquet(df, "copom_trechos")


# ------------------------------------------------------------------ decisões de Selic


def decisoes() -> pd.DataFrame:
    """Cada ata ↔ Selic meta vigente antes e definida naquela reunião.

    `meta_selic_copom` (SGS 432) é diária; a mudança entra no dia seguinte
    ao da agradecimento final da reunião (2º dia, que define `data` da ata).
    """
    sgs = ler_parquet("sgs")
    s = (sgs[sgs.serie == "meta_selic_copom"]
         .assign(data=lambda d: pd.to_datetime(d.data))
         .set_index("data")["valor"]
         .sort_index())
    linhas = []
    for _, row in carrega_catalogo().iterrows():
        d = pd.Timestamp(row.data)
        antes = s[s.index <= d]
        depois = s[s.index > d]
        selic_antes = float(antes.iloc[-1]) if len(antes) else None
        selic_depois = float(depois.iloc[0]) if len(depois) else None
        delta = (None if selic_antes is None or selic_depois is None
                 else round((selic_depois - selic_antes) * 100))
        linhas.append({
            "num": int(row.num), "data": row.data, "ano": int(row.ano),
            "selic_antes": selic_antes, "selic_depois": selic_depois,
            "delta_bp": delta,
        })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ CLI


def main() -> None:
    cat = carrega_atas()
    print(f"catálogo: {len(cat)} atas ({cat.num.min()}–{cat.num.max()}), "
          f"frases: {cat.n_frases.min()}–{cat.n_frases.max()}")

    mat = temas()
    if not mat.empty:
        cols = [c for c in TEMAS if c in mat.columns]  # temas sem ocorrência
        ausentes = [c for c in TEMAS if c not in mat.columns]
        resumo = mat.groupby("ano")[cols].sum()
        print("\n== matriz resumo (ano × tema, nº de frases) ==")
        print(resumo.to_string())
        if ausentes:
            print("\ntemas sem nenhuma ocorrência no corpus:", ausentes)
    else:
        print("\nnenhuma ocorrência de tema")

    d = decisoes()
    mov = d[d.delta_bp.fillna(0) != 0]
    print(f"\n== reuniões com mudança de Selic: {len(mov)} de {len(d)} ==")
    print(mov[["num", "data", "selic_antes", "selic_depois", "delta_bp"]]
          .to_string(index=False))

    p = salvar_trechos()
    print("\nok:", p)


if __name__ == "__main__":
    main()
