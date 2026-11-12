# Gera notebooks/08_renda_salarios.ipynb (estilo nb05)
#
# ATENÇÃO: sobrescreve o notebook inteiro e PERDE os outputs executados —
# depois de rodar, reexecute com
#   env PYTHONPATH=. conda run -n juros_divida jupyter nbconvert --to notebook \
#       --execute --inplace notebooks/08_renda_salarios.ipynb
# e confira com scripts/checa_figuras.py.
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb.metadata["language_info"] = {"name": "python", "version": "3.12"}

md_intro = """\
# 8 · Renda, salários e investimento: o que os dados mostram (2002–2026)

**O que este notebook FAZ com dados:** fecha a lacuna de evidência sobre
*emprego, renda e investimento* do artigo, com quatro famílias de séries:

1. rendimento médio mensal da PNAD Contínua (nominal e real, desde 2012);
2. massa de rendimento × média — daí sai a ocupação implícita;
3. salário mínimo nominal e seu poder de compra (deflacionado pelo INPC);
4. FBCF contra o PIB, com o juro real ex ante sobreposto como marcador factual.

**O que este notebook NÃO faz nesta fase:**

- **não** estima produtividade — a série oficial (PNAD/EC1034) fica para a
  2ª iteração; produtividade contábil não é a mesma coisa que renda;
- **não** infere causalidade: o overlay de juro real é temporal, não causal;
- **não** conclui o 3º ponto do artigo antes de olhar esses dados.

**Limites declarados de saída:** PNAD Contínua começa em 2012 (sem comparação
com 2002–11 nesta fonte); 2026 é ano incompleto (rendimento e FBCF até o
2º trimestre)."""

c_imports = """\
import sys
from pathlib import Path
p = Path.cwd()
while not (p / "src").exists() and p != p.parent:
    p = p.parent
sys.path.insert(0, str(p))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

pd.set_option("display.width", 170)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

from src.viz.graficos import (
    estilo, salvar, AZUL, VERMELHO, VERDE, LARANJA, ROXO, CINZA, CORES_DETENTOR,
)
from src.processa import indicadores as ind

estilo()
print("diretório de dados:", p / "dados" / "processado")"""

c_carga = """\
sgs = pd.read_parquet(p / "dados" / "processado" / "sgs.parquet")
rend = pd.read_parquet(p / "dados" / "processado" / "rendimento.parquet")
fbcf = pd.read_parquet(p / "dados" / "processado" / "fbcf.parquet")
sal = pd.read_csv(p / "dados" / "bruto" / "salario_minimo.csv",
                  comment="#", parse_dates=["vigente_desde"])

def _mensal(nome):
    return sgs[sgs.serie == nome].set_index("data")["valor"]

# índices acumulados de preços, base jan/2002 = 100
def _acum(s):
    c = (1 + s / 100).cumprod()
    return c / c.iloc[0] * 100

ipca, inpc = _acum(_mensal("ipca")), _acum(_mensal("inpc"))
print(f"preços acumulados jan/02 -> {ipca.index[-1]:%m/%Y}: "
      f"IPCA {ipca.iloc[-1]:.1f} | INPC {inpc.iloc[-1]:.1f} "
      f"({inpc.iloc[-1] - ipca.iloc[-1]:+.1f} p.p.)")

# salário mínimo: steps do CSV -> série mensal; poder de compra em R$ do
# último mês do INPC (deflação acumulada)
meses = pd.date_range("2002-01-01", inpc.index.max(), freq="MS")
sm = sal.set_index("vigente_desde")["salario_minimo_nominal"]
sal_m = sm.reindex(meses.union(sm.index)).ffill().reindex(meses)
sal_real = sal_m * inpc.iloc[-1] / inpc.reindex(sal_m.index).ffill()
print(f"salário mínimo: R$ {sal_m.iloc[0]:.0f} (jan/02) -> "
      f"R$ {sal_m.iloc[-1]:.0f} ({sal_m.index[-1]:%m/%Y}) = "
      f"{sal_m.iloc[-1] / sal_m.iloc[0]:.1f}x nominal | em R$ de "
      f"{inpc.index[-1]:%m/%Y}: R$ {sal_real.iloc[0]:.0f} -> "
      f"R$ {sal_real.iloc[-1]:.0f} ({sal_real.iloc[-1] / sal_real.iloc[0]:.1f}x)")

def marcar(ax, rotulos=True):
    \"\"\"Marcadores de período pedidos para o artigo (datas factuais).\"\"\"
    tr = ax.get_xaxis_transform()
    ax.axvspan(pd.Timestamp("2013-01-01"), pd.Timestamp("2016-12-31"),
               color=VERDE, alpha=0.06, zorder=0)
    ax.text(pd.Timestamp("2014-06-30"), 0.97, "2013–16", transform=tr,
            ha="center", va="top", fontsize=8, color=VERDE)
    ax.axvline(pd.Timestamp("2016-08-31"), color=CINZA, ls=":", lw=1.2, zorder=2)
    ax.axvline(pd.Timestamp("2017-01-01"), color=VERMELHO, ls="--", lw=1.2, zorder=2)
    if rotulos:
        # em altura menor que "2013–16" para não colidir com ele
        ax.text(pd.Timestamp("2016-08-25"), 0.88, "impeachment\\n(ago/16)",
                transform=tr, ha="right", va="top", fontsize=8, color=CINZA)
        ax.text(pd.Timestamp("2017-02-01"), 0.97, "2017: desandou",
                transform=tr, ha="left", va="top", fontsize=8, color=VERMELHO)"""

c_renda = """\
an = rend[rend.frequencia == "anual"]
med_nom = an[(an.tabela == "4660") & (an.variavel == "5929")].set_index("data")["valor"]
med_real = an[(an.tabela == "4660") & (an.variavel == "5933")].set_index("data")["valor"]
# A variável trimestral tem lacuna (coleta PNAD suspensa na pandemia) e
# deflação com base própria — nível não comparável com o anual; fica de fora
# do gráfico e é registrada aqui.
tri = rend[(rend.frequencia == "trimestral") & (rend.variavel == "5933")]
faltam = sorted({f"{a}{q:02d}" for a in range(2012, 2027) for q in (1, 2, 3, 4)}
                - {"202603", "202604"} - set(tri.periodo_codigo))
print(f"série trimestral: {len(tri)} de 58 tri | lacuna: "
      f"{[f'{c[:4]}Q{int(c[4:])}' for c in faltam]}")

tab = pd.DataFrame({"nominal": med_nom, "real": med_real})
tab["real var. %"] = med_real.pct_change() * 100
tab.index = tab.index.year
print(tab.round(0).to_string())

g = lambda ano: float(med_real[med_real.index.year == ano].iloc[0])
gn = lambda ano: float(med_nom[med_nom.index.year == ano].iloc[0])
print(f"real: 2014 {g(2014):.0f} -> 2022 {g(2022):.0f} "
      f"({100 * (g(2022) / g(2014) - 1):+.1f}%) -> 2025 {g(2025):.0f} "
      f"({100 * (g(2025) / g(2022) - 1):+.1f}% vs 2022, "
      f"{100 * (g(2025) / g(2014) - 1):+.1f}% vs 2014)")
print(f"nominal 2012->2025: {100 * (gn(2025) / gn(2012) - 1):+.0f}%")

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(med_nom.index, med_nom, color=AZUL, marker="o", lw=2,
        label="nominal (anual)")
ax.plot(med_real.index, med_real, color=VERMELHO, marker="o", lw=2,
        label="real (anual)")
marcar(ax)
ax.annotate(f"pico 2014: R$ {g(2014):,.0f}".replace(",", "."),
            xy=(pd.Timestamp("2014-12-31"), g(2014)),
            xytext=(-104, 30), textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8), fontsize=9)
ax.annotate(f"fundo 2022: R$ {g(2022):,.0f}".replace(",", "."),
            xy=(pd.Timestamp("2022-12-31"), g(2022)),
            xytext=(14, -30), textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8), fontsize=9)
ax.annotate(f"recorde 2025: R$ {g(2025):,.0f}".replace(",", "."),
            xy=(pd.Timestamp("2025-12-31"), g(2025)),
            xytext=(-64, 14), textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8), fontsize=9)
ax.set_ylabel("R$ (real = deflacionado pelo IBGE)")
ax.set_title("Rendimento médio da PNAD: o nominal sobe sempre; o real só supera 2014 em 2024")
ax.legend(fontsize=9, loc="lower right")
ax.margins(x=0.02, y=0.14)
salvar(fig, "08_renda_media")"""

c_precos = """\
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(ipca.index, ipca, color=AZUL, lw=1.8, label=f"IPCA ({ipca.iloc[-1]:.0f})")
ax1.plot(inpc.index, inpc, color=VERMELHO, lw=1.8, label=f"INPC ({inpc.iloc[-1]:.0f})")
marcar(ax1, rotulos=False)
ax1.set_title("Preços acumulados, jan/2002 = 100")
ax1.legend(fontsize=10)
ax1.margins(x=0.01)

def _acc12(s):
    return ((1 + s / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100

# diferença em 12 meses sobre as VARIAÇÕES mensais (não sobre o índice)
ipca_m, inpc_m = _mensal("ipca"), _mensal("inpc")
dif = (_acc12(inpc_m) - _acc12(ipca_m)).dropna()
dif_anual = dif.groupby(dif.index.year).mean()
dif_anual = dif_anual[dif_anual.index >= 2003]
ax2.bar(dif_anual.index, dif_anual, width=0.7,
        color=[VERMELHO if v >= 0 else AZUL for v in dif_anual])
ax2.axhline(0, color="k", lw=1)
ax2.set_title("INPC − IPCA: média da variação em 12 meses (p.p.)")
ax2.set_ylabel("p.p. (+ INPC acima)")
print(f"diferença acumulada: {inpc.iloc[-1] - ipca.iloc[-1]:+.1f} p.p. em "
      f"{len(ipca) / 12:.0f} anos | INPC acima em: "
      f"{[a for a, v in dif_anual.items() if v > 0]}")
salvar(fig, "08_ipca_inpc")"""

c_salario = """\
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fmt = FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", "."))
for ax, s, cor, titulo in (
    (ax1, sal_m, AZUL, "Nominal (R$ correntes)"),
    (ax2, sal_real, VERMELHO,
     f"Poder de compra (R$ de {inpc.index[-1]:%m/%Y}, deflacionado pelo INPC)"),
):
    ax.step(s.index, s.values, where="post", color=cor, lw=2.2)
    ax.yaxis.set_major_formatter(fmt)
    ax.set_title(titulo)
    marcar(ax, rotulos=(ax is ax1))
ax1.annotate("R$ 1.045 em fev/20",
             xy=(pd.Timestamp("2020-02-01"), 1045),
             xytext=(24, 26), textcoords="offset points", fontsize=9,
             arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
ax2.annotate(f"R$ {sal_real.iloc[0]:.0f} em 2002\\n(precos de hoje)",
             xy=(sal_real.index[0], float(sal_real.iloc[0])),
             xytext=(46, 40), textcoords="offset points", fontsize=9,
             arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
print(f"nominal {sal_m.iloc[-1] / sal_m.iloc[0]:.1f}x vs real "
      f"{sal_real.iloc[-1] / sal_real.iloc[0]:.1f}x | 2019 real: "
      f"R$ {sal_real.loc['2019-01-01']:.0f} -> hoje R$ {sal_real.iloc[-1]:.0f} "
      f"({100 * (sal_real.iloc[-1] / sal_real.loc['2019-01-01'] - 1):+.1f}%)")
print(f"nota: o INPC caiu em 2026, então jan/26 aparece como "
      f"R$ {sal_real.loc['2026-01-01']:.0f} em preços de {inpc.index[-1]:%m/%Y}")
salvar(fig, "08_salario_minimo")"""

c_massa = """\
massa_real = an[(an.tabela == "4663") & (an.variavel == "6293")].set_index("data")["valor"]
# razão massa/média: cancela a base de preços e dá ocupadas com rendimento
ocupadas = massa_real / med_real
idx12 = lambda s: s / s.iloc[0] * 100

gm = lambda ano: float(massa_real[massa_real.index.year == ano].iloc[0])
go = lambda ano: float(ocupadas[ocupadas.index.year == ano].iloc[0])
print(f"2012->2025: massa real {100 * (gm(2025) / gm(2012) - 1):+.1f}% | "
      f"média real {100 * (g(2025) / g(2012) - 1):+.1f}%")
print(f"ocupadas com rendimento (implícito): {go(2012):.1f} -> {go(2025):.1f} mi "
      f"({100 * (go(2025) / go(2012) - 1):+.1f}%) | 2020: {go(2020):.1f} mi")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(med_real.index, idx12(med_real), color=VERMELHO, marker="o", lw=2,
         label="rendimento médio real")
ax1.plot(massa_real.index, idx12(massa_real), color=AZUL, marker="o", lw=2,
         label="massa de rendimento real")
marcar(ax1, rotulos=False)
ax1.axhline(100, color="gray", lw=0.8)
ax1.set_title("2012 = 100: média × massa (massa = média × ocupadas)")
ax1.legend(fontsize=9)

ax2.plot(ocupadas.index, ocupadas, color=VERDE, lw=2.2)
marcar(ax2)
ax2.annotate(f"pandemia: {go(2020):.0f} mi em 2020",
             xy=(pd.Timestamp("2020-12-31"), go(2020)),
             xytext=(-96, 40), textcoords="offset points", fontsize=9,
             arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
ax2.set_title("Ocupadas com rendimento (milhões, implícito)")
ax2.set_ylabel("milhões")
salvar(fig, "08_massa_ocupacao")"""

c_fbcf = """\
pib = fbcf[fbcf.setor.str.contains("PIB")].set_index("data")["indice"]
fbc = fbcf[fbcf.setor.str.contains("capital fixo")].set_index("data")["indice"]
_rebase = lambda s: s / s[s.index.year == 2002].mean() * 100
fbc_r, pib_r = _rebase(fbc), _rebase(pib)
fbc_yoy = (fbc / fbc.shift(4) - 1) * 100

# overlay factual do juro real ex ante (média do trimestre), sem causalidade
jr = ind.selic_real_mensal()["juro_real_ex_ante"].dropna()
jr_tri = jr.groupby(jr.index.to_period("Q")).mean()
jr_tri.index = jr_tri.index.to_timestamp(how="end")

def _janela(a, b):
    s = fbc_yoy[(fbc_yoy.index.year >= a) & (fbc_yoy.index.year <= b)]
    return s.mean()

print(f"FBCF 2002=100: 2014-12 {fbc_r.asof('2014-12-31'):.0f} | "
      f"2025-12 {fbc_r.asof('2025-12-31'):.0f} | {fbc_r.index[-1]:%Y-%m} "
      f"{fbc_r.iloc[-1]:.0f}")
print(f"PIB  2002=100: 2014-12 {pib_r.asof('2014-12-31'):.0f} | "
      f"2025-12 {pib_r.asof('2025-12-31'):.0f} | {pib_r.index[-1]:%Y-%m} "
      f"{pib_r.iloc[-1]:.0f}")
print(f"FBCF var. anual média: 2013-16 {_janela(2013, 2016):+.1f}% | "
      f"2017-19 {_janela(2017, 2019):+.1f}% | 2023-25 {_janela(2023, 2025):+.1f}%")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
ax1.plot(fbc_r.index, fbc_r, color=VERMELHO, lw=1.8, label="FBCF (volume)")
ax1.plot(pib_r.index, pib_r, color=AZUL, lw=1.8, label="PIB (volume)")
marcar(ax1)
ax1.axhline(100, color="gray", lw=0.8)
ax1.set_title("FBCF e PIB em volume, 2002 = 100")
ax1.legend(fontsize=10, loc="upper left")
ax1.margins(y=0.06)

fy = fbc_yoy.dropna()
ax2.bar(fy.index, fy, width=80, color=[VERDE if v >= 0 else VERMELHO for v in fy],
        label="FBCF, var. % em 12 meses")
ax2.axhline(0, color="k", lw=1)
marcar(ax2, rotulos=False)
ax2.set_ylabel("% em 12 meses")
ax3 = ax2.twinx()
ax3.plot(jr_tri.index, jr_tri, color="black", lw=1.6, ls="--",
         label="juro real ex ante (média do trimestre)")
ax3.set_ylabel("% a.a.")
ax3.grid(False)
h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax3.get_legend_handles_labels()
ax2.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left")
ax2.set_title("Investimento e juro real ex ante — overlay factual, sem causalidade")
salvar(fig, "08_fbcf_pib")"""

md_achados = """\
**Achados verificáveis (bloco novo do artigo).**

- **Renda (PNAD, desde 2012):** o rendimento médio real bateu recorde em
  **2025 (R$ 3.560)**, +17,4% sobre o fundo de 2022 (R$ 3.032) e +8,5% sobre
  o pico de 2014 (R$ 3.280) — mas só superou 2014 em **2024**. O nominal
  subiu +140% de 2012 a 2025 e a inflação comeu a maior parte: a comparação
  certa é a real. **São duas fases, não uma**: alta até 2014, erosão até
  2022, recuperação 2023–25. Isso *parcialmente confirma* a expectativa de
  "salário sem ganho real" (2015–2022) e *parcialmente contrapõe* (2023–25).
- **Massa × média:** a massa real cresceu **+36%** (2012–2025) contra **+15,5%**
  da média — a diferença é ocupação: as pessoas com rendimento de trabalho
  passaram de **~86 mi (2012) para ~102 mi (2025)**, com queda para 83 mi em
  2020. Renda maior *e* mais gente ocupada puxam a massa.
- **Salário mínimo:** de R$ 180 (jan/02) a R$ 1.621 (jan/26), **9,0× em
  nominal**; deflacionado pelo INPC, o poder de compra subiu **2,1×**
  (R$ 766 → R$ 1.621 em R$ de set/2026). Entre 2019 e 2026 o ganho real foi
  de **+8%** — o piso não explica sozinho a recuperação de renda.
- **Preços:** IPCA e INPC acumulam quase o mesmo desde 2002 (422 × 426), mas
  o INPC correndo **acima** em 2015–16 e 2019–22 e **abaixo** em 2017–18 e
  2023–26 — a cesta do trabalhador não infla igual à média da economia.
- **Investimento:** a FBCF em volume chegou a **176 em 2014** (2002=100) e
  estava em **168 em 2025** — 11 anos sem recuperar o patamar — enquanto o
  PIB foi de 151 a 166. Variação anual média da FBCF: **−6,0% em 2013–16**,
  +2,2% em 2017–19, +2,4% em 2023–25. O juro real ex ante no overlay é
  factual (**sem causalidade**): o aperto de 2015–16 coincide com a maior
  queda do investimento da série.

**Limites declarados:** PNAD começa em 2012; 2026 incompleto (2º tri); a
série *trimestral* de rendimento tem lacuna de 2020Q2 a 2022Q1 (coleta
suspensa na pandemia) e deflação com base própria — por isso o gráfico usa
só a anual; "ocupadas" da massa é implícito (massa ÷ média), não a série
oficial de ocupação; a série real do IBGE é recalculada a cada divulgação;
produtividade **não** está aqui.

**Pendência da 2ª iteração do nb08:** produtividade (PNAD, horas
trabalhadas/EC1034) — produtividade contábil não é renda, e o 3º ponto do
artigo só fecha depois dela."""

nb.cells = [
    nbf.v4.new_markdown_cell(md_intro),
    nbf.v4.new_code_cell(c_imports),
    nbf.v4.new_code_cell(c_carga),
    nbf.v4.new_code_cell(c_renda),
    nbf.v4.new_code_cell(c_precos),
    nbf.v4.new_code_cell(c_salario),
    nbf.v4.new_code_cell(c_massa),
    nbf.v4.new_code_cell(c_fbcf),
    nbf.v4.new_markdown_cell(md_achados),
]
destino = Path(__file__).resolve().parents[1] / "notebooks" / "08_renda_salarios.ipynb"
nbf.write(nb, destino)
print("ok ->", destino)
