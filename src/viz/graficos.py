"""Helpers gráficos compartilhados (notebooks + app Streamlit)."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[2]
FIGS = RAIZ / "viz" / "figs"

# paleta consistente por dtype
AZUL = "#1f77b4"
VERMELHO = "#d62728"
VERDE = "#2ca02c"
LARANJA = "#ff7f0e"
ROXO = "#9467bd"
MARROM = "#8c564b"
CINZA = "#7f7f7f"

CORES_DETENTOR = {
    "Instituições Financeiras": "#d62728",
    "Fundos de Investimento": "#ff7f0e",
    "Previdência": "#1f77b4",
    "Não-residentes": "#9467bd",
    "Tesouro Direto": "#2ca02c",
    "Seguradoras": "#8c564b",
    "Governo": "#7f7f7f",
    "Outros": "#bcbd22",
}


def estilo() -> None:
    mpl.rcParams.update({
        "figure.figsize": (10, 5),
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "legend.frameon": False,
    })


def salvar(fig, nome: str) -> Path:
    """Salva figura em viz/figs/{nome}.png e retorna o caminho."""
    FIGS.mkdir(parents=True, exist_ok=True)
    destino = FIGS / f"{nome}.png"
    fig.tight_layout()
    fig.savefig(destino, bbox_inches="tight")
    plt.close(fig)
    print(f"fig -> {destino.relative_to(RAIZ)}")
    return destino
