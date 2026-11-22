# Verifica colisoes de texto/legendas nas figuras de um notebook (sem depender de imagem)
# Uso: env PYTHONPATH=. conda run -n juros_divida python scripts/checa_figuras.py [notebook]
# Sem argumento, checa o nb08.
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(p))

alvo = (Path(sys.argv[1]) if len(sys.argv) > 1
        else p / "notebooks" / "08_renda_salarios.ipynb")
print("checando:", alvo)
nb = json.loads(alvo.read_text())
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
                    print(f"[{nome}] SOBREPOSIÇÃO: {bbs[a][0]}  X  {bbs[b][0]}  "
                          f"({area:.0f} px^2)")
        # texto fora do que será salvo? salvar() faz tight_layout() +
        # savefig(bbox_inches="tight", pad=0,1"), então compara com o bbox
        # APERTADO da figura (inches -> px) mais o pad — e não com fig.bbox
        # (canvas original), que marcaria falso positivo para legendas
        # ancoradas fora dos eixos, que o tight inclui corretamente.
        pad_px = plt.rcParams.get("savefig.pad_inches", 0.1) * fig.dpi
        fb = fig.get_tightbbox(r).transformed(fig.dpi_scale_trans)
        fb = fb.expanded(1 + 2 * pad_px / max(fb.width, 1),
                         1 + 2 * pad_px / max(fb.height, 1))
        for rot, bb in bbs:
            if bb.x0 < fb.x0 - 1 or bb.x1 > fb.x1 + 1 or bb.y0 < fb.y0 - 1 or bb.y1 > fb.y1 + 1:
                total_problemas += 1
                print(f"[{nome}] FORA DA FIGURA: {rot}")

print("---")
print("figuras:", list(figs))
print("problemas:", total_problemas)
