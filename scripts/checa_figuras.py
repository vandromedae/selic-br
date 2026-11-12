# Verifica colisoes de texto/legendas nas figuras do nb08 (sem depender de imagem)
# Uso: env PYTHONPATH=. conda run -n juros_divida python scripts/checa_figuras.py
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(p))

nb = json.loads((p / "notebooks" / "08_renda_salarios.ipynb").read_text())
ns = {"__name__": "__main__"}

figs = {}


def salvar_guarda(fig, nome):
    figs[nome] = fig
    return Path(nome)


exec_cel = [c for c in nb["cells"] if c["cell_type"] == "code"]
for i, c in enumerate(exec_cel):
    src = "".join(c["source"])
    exec(compile(src, f"celula_{i}", "exec"), ns)
    if i == 0:  # apos imports, troca salvar para nao fechar as figuras
        ns["salvar"] = salvar_guarda

plt.close("all")

def bbox(t, r):
    try:
        return t.get_window_extent(renderer=r)
    except Exception:
        return None

def inter(a, b):
    x0 = max(a.x0, b.x0); x1 = min(a.x1, b.x1)
    y0 = max(a.y0, b.y0); y1 = min(a.y1, b.y1)
    return max(0, x1 - x0) * max(0, y1 - y0)

total_problemas = 0
from matplotlib.backends.backend_agg import FigureCanvasAgg
for nome, fig in figs.items():
    FigureCanvasAgg(fig)  # garante canvas Agg com get_renderer()
    fig.canvas.draw()     # layout completo antes de medir
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        itens = []
        for t in ax.texts:
            itens.append((repr(t.get_text())[:40], t))
        if ax.get_title():
            itens.append(("TITLE: " + ax.get_title()[:40], ax.title))
        for lg in [ax.get_legend()]:
            if lg is not None:
                for t in lg.get_texts():
                    itens.append(("LEGEND: " + t.get_text()[:30], t))
        bbs = [(rot, bbox(t, r)) for rot, t in itens]
        bbs = [(rot, bb) for rot, bb in bbs if bb is not None and bb.width > 0]
        for a in range(len(bbs)):
            for b in range(a + 1, len(bbs)):
                area = inter(bbs[a][1], bbs[b][1])
                if area > 25:  # px^2
                    total_problemas += 1
                    print(f"[{nome}] SOPOSIÇÃO: {bbs[a][0]}  X  {bbs[b][0]}  "
                          f"({area:.0f} px^2)")
        # texto fora da figura?
        fb = fig.bbox
        for rot, bb in bbs:
            if bb.x0 < fb.x0 - 1 or bb.x1 > fb.x1 + 1 or bb.y0 < fb.y0 - 1 or bb.y1 > fb.y1 + 1:
                total_problemas += 1
                print(f"[{nome}] FORA DA FIGURA: {rot}")

print("---")
print("figuras:", list(figs))
print("problemas:", total_problemas)
