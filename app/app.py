"""Ferramenta web: juros e dívida pública — Brasil (2002–2026).

Orquestração: sidebar + dispatch das páginas. O conteúdo está em
`app/paginas.py`, as figuras em `app/graficos.py`, as tabelas em
`app/tabelas.py` e o carregamento em `app/dados.py` — reaproveitando
`src/processa/indicadores.py` (núcleo analítico) e a paleta de
`src/viz/graficos.py`.

Rodar: `streamlit run app/app.py` (ambiente conda juros_divida, na raiz do repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

st.set_page_config(
    page_title="Juros e Dívida — Transparência",
    page_icon="🏦",
    layout="wide",
)

from app.dados import ANO_CORTE, _assinatura_dados, dados  # noqa: E402
from app import paginas  # noqa: E402
from app.tabelas import fmt_bi, fmt_pct, resumo  # noqa: E402

D = dados(_assinatura_dados())

# ------------------------------------------------------------------ sidebar

st.sidebar.title("🏦 Juros e dívida pública")
st.sidebar.caption(f"Brasil, 2002–{ANO_CORTE} · apenas fontes públicas")

PAGINA = st.sidebar.radio(
    "Pergunta",
    [
        "Visão geral",
        "P1 · Os juros se justificam?",
        "P2 · Quem recebe os juros?",
        "P3 · Os juros amortizam a dívida?",
        "P4 · Os juros geram capital produtivo?",
        "P5 · Houve propositalidade?",
        "Transparência: lacunas",
        "Fontes e metodologia",
    ],
    label_visibility="collapsed",
)
st.sidebar.divider()

r = resumo(D)
with st.sidebar.expander("📌 números-chave", expanded=True):
    st.markdown(f"""
**Juros nominais ({r['ultimo_ano_completo']}):** {fmt_bi(r['row'].juros_mi / 1000)}
· {fmt_pct(r['row'].juros_pib_pct)} do PIB

**Swaps ({r['ultimo_ano_completo']}):** {r['row'].swap_pp_pib:+.2f} p.p. do PIB
({"aumentam" if r['row'].swap_pp_pib > 0 else "reduzem"} os juros)

**Custo médio DPF:** {fmt_pct(r['cm_val'])} a.a. ({r['cm_ult']:%m/%Y})

**Selic meta:** {fmt_pct(D['macro'].loc[r['m_ult']].selic_meta)} a.a.
({r['m_ult']:%m/%Y}) · **IPCA 12m:** {fmt_pct(D['macro'].loc[r['m_ult']].ipca_12m)}

**Estoque DPMFi:** {fmt_bi(D['detentores'][D['detentores'].data == r['dez_ult']].valor_bi.sum(), 0)}
({r['dez_ult']:%m/%Y})
""")

st.sidebar.divider()
st.sidebar.caption(
    "Análise de dados, não posicionamento. A tese de “propositalidade” "
    "(P5) exige documentos — fase posterior. Nomes de credores "
    "individuais não são públicos (Req. 696/2019 negado)."
)

# ============================================================ páginas

if PAGINA == "Visão geral":
    paginas.visao_geral(D)
elif PAGINA.startswith("P1"):
    paginas.p1(D)
elif PAGINA.startswith("P2"):
    paginas.p2(D)
elif PAGINA.startswith("P3"):
    paginas.p3(D)
elif PAGINA.startswith("P4"):
    paginas.p4(D)
elif PAGINA.startswith("P5"):
    paginas.p5(D)
elif PAGINA == "Transparência: lacunas":
    paginas.transparencia()
else:
    paginas.fontes()
