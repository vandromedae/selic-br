"""Carregamento dos dados processados (cache por assinatura)."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import streamlit as st

from src.processa import indicadores as ind

# ano incompleto: excluído dos gráficos e tabelas anuais fechados
# (regra 4 em "Fontes e metodologia")
ANO_CORTE = 2026


def _assinatura_dados() -> tuple[tuple[str, int, int], ...]:
    """(nome, mtime_ns, tamanho) de cada arquivo em dados/processado.

    Chave de invalidação do cache: sem parâmetro, o @st.cache_data hasheia
    sempre a mesma chave e o app exibiria dados velhos mesmo depois de
    rodar os extratores. O parâmetro de dados() entra no hash — não pode
    começar com "_", senão o Streamlit o ignora de propósito.
    """
    proc = RAIZ / "dados" / "processado"
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size)
                 for p in sorted(proc.iterdir()) if p.is_file())


def dados(assinatura) -> dict[str, pd.DataFrame]:
    del assinatura  # só serve para invalidar o cache quando os arquivos mudam
    j = ind.juros_anuais()
    f = ind.fatores_anuais()
    dz = ind.detentores_anuais()
    jd = ind.juros_por_detentor()
    mm = ind.selic_real_mensal()
    cm = ind.custo_medio_dpf()
    val = ind.validacao_bndes()
    return {
        "juros": j,
        "fatores": f,
        "detentores": dz,
        "juros_detentor": jd,
        "macro": mm,
        "custo": cm,
        "validacao_bndes": val,
    }
