# Gera notebooks/09_justificativas.ipynb (estilo nb08)
#
# ATENÇÃO: sobrescreve o notebook inteiro e PERDE os outputs executados —
# depois de rodar, reexecute com
#   env PYTHONPATH=. conda run -n juros_divida jupyter nbconvert --to notebook \
#       --execute --inplace notebooks/09_justificativas.ipynb
# e confira as figuras em viz/figs/09_*.png.
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {
    "display_name": "Python 3", "language": "python", "name": "python3"}
nb.metadata["language_info"] = {"name": "python", "version": "3.12"}

md_intro = """\
# 9 · Justificativas do BC para o juro alto: o que os dados mostram (2012–2026)

**Pergunta:** as justificativas usadas pelo Banco Central para sustentar o
juro alto — inflação acima da meta, mercado de trabalho aquecido, rendimentos
crescendo acima da produtividade, expectativas desancoradas, choques de
oferta — se sustentam nos dados?

**O que este notebook FAZ:**

1. compara o IPCA com a **meta efetiva de cada ano** (não com a simplificação
   "4,5% até 2024");
2. decompõe o IPCA 12m por grupo do IPCA (aproximação declarada, com resíduo);
3. estima curvas de Phillips simples para o IPCA cheio e para serviços, com
   erro-padrão HAC — **associação condicional, não causalidade**;
4. mede salário real, produtividade por trabalhador e ULC;
5. descreve o mercado de trabalho (desemprego, ocupação, participação,
   informalidade);
6. lê o Focus (base de cálculo 0) e as atas 280–282, com citação verbatim;
7. fecha com a tabela **"o que o BC diz / o que os dados mostram"**.

**O que este notebook NÃO faz:**

- **não** identifica causalidade: a Phillips é correlação condicional; a
  decomposição é contábil; o juro alto não é tratado como causa única;
- **não** mede produtividade por hora (a PNAD agregada não publica horas no
  SIDRA) — usa produtividade por trabalhador;
- **não** transforma discurso ou entrevista em dado: as atas são citadas
  verbatim; entrevistas só entrariam com transcrição literal;
- **não** conclui qual é o "prêmio institucional" — apenas mostra o que os
  dados permitem e o que não permitem.

**Fontes:** SGS/BCB (IPCA, serviços, câmbio), SIDRA/IBGE (IPCA por grupos,
PNAD Contínua, PIB volume), Focus/Olinda (base 0), atas do Copom 280–282.
Tudo em `dados/processado/`; nenhum download neste notebook."""

c_imports = r"""\
import sys
import textwrap
from pathlib import Path

p = Path.cwd()
while not (p / "src").exists() and p != p.parent:
    p = p.parent
sys.path.insert(0, str(p))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display

pd.set_option("display.width", 180)
pd.set_option("display.max_colwidth", 120)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

from src.viz.graficos import (
    estilo, salvar, AZUL, VERMELHO, VERDE, LARANJA, ROXO, MARROM, CINZA,
)
from src.processa import justificativas as j

estilo()
print("dados:", p / "dados" / "processado")"""

c_metas = r"""\
m = j.metas_anuais()
tab = m[["ano", "meta_pct", "tolerancia_pp", "piso_pct", "teto_pct",
         "ipca_pct", "fechado", "dentro", "abaixo_piso", "acima_teto"]].rename(
    columns={
        "ano": "ano",
        "meta_pct": "meta (%)",
        "tolerancia_pp": "± (p.p.)",
        "piso_pct": "piso (%)",
        "teto_pct": "teto (%)",
        "ipca_pct": "IPCA (%)",
        "fechado": "ano fechado?",
        "dentro": "dentro?",
        "abaixo_piso": "abaixo do piso?",
        "acima_teto": "acima do teto?",
    })
display(tab)
print("2026: a coluna IPCA é o 12m de out/26, não o acumulado no ano.")"""

c_metas_fig = r"""\
sgs = pd.read_parquet(p / "dados" / "processado" / "sgs.parquet")
ipca12 = (sgs[sgs.serie == "ipca_12m"]
          .assign(data=lambda d: pd.to_datetime(d["data"]))
          .set_index("data")["valor"].sort_index())
ipca12 = ipca12[ipca12.index >= "2012-01-01"]

meta = pd.Series([j.METAS_ANUAIS[a][0] for a in ipca12.index.year],
                 index=ipca12.index)
tol = pd.Series([j.METAS_ANUAIS[a][1] for a in ipca12.index.year],
                index=ipca12.index)

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.fill_between(ipca12.index, meta - tol, meta + tol, color=CINZA,
                alpha=0.15, label="faixa de tolerância")
ax.plot(meta.index, meta, color=CINZA, ls="--", lw=1.2, label="meta")
ax.plot(ipca12.index, ipca12, color=AZUL, lw=1.8, label="IPCA 12m")

dez = ipca12[ipca12.index.month == 12]
cores = []
for d, v in dez.items():
    mm, tt = j.METAS_ANUAIS[d.year]
    cores.append(VERMELHO if v > mm + tt else (LARANJA if v < mm - tt else VERDE))
ax.scatter(dez.index, dez.values, c=cores, s=28, zorder=5, edgecolor="white")
for cor, rotulo in ((VERMELHO, "acima do teto"), (LARANJA, "abaixo do piso"),
                    (VERDE, "dentro")):
    ax.scatter([], [], color=cor, s=28, label=rotulo)
if ipca12.index.max().year == 2026:
    ax.annotate(f"out/26: {ipca12.iloc[-1]:.2f}%",
                xy=(ipca12.index[-1], ipca12.iloc[-1]),
                xytext=(-70, 22), textcoords="offset points", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
ax.set_ylabel("% em 12 meses")
ax.set_title("IPCA 12m contra a meta efetiva e a faixa de tolerância")
ax.legend(fontsize=9, ncol=3, loc="upper right")
ax.margins(x=0.01)
salvar(fig, "09_metas")"""

c_contrib = r"""\
c = j.contribuicoes_ipca()
s = j.servicos_intensivos()

serv = (sgs[sgs.serie == "ipca_servicos"]
        .assign(data=lambda d: pd.to_datetime(d["data"]))
        .set_index("data")["valor"].sort_index())
serv12 = ((1 + serv / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100

def _serv12(ano):
    ref = (pd.Timestamp(f"{ano}-12-31") if ano < 2026
           else pd.Timestamp("2026-10-31"))
    return float(serv12.asof(ref))

linhas = []
for ano in range(2021, 2027):
    d = c[c.ano == ano].sort_values("contribuicao_pp", ascending=False)
    ss = s[s.ano == ano].iloc[0]
    top = d.head(3)
    linhas.append({
        "ano": ano,
        "IPCA 12m (%)": d.total_ipca_12m.iloc[0],
        "1º grupo": f"{top.iloc[0].grupo} ({top.iloc[0].contribuicao_pp:.2f})",
        "2º grupo": f"{top.iloc[1].grupo} ({top.iloc[1].contribuicao_pp:.2f})",
        "3º grupo": f"{top.iloc[2].grupo} ({top.iloc[2].contribuicao_pp:.2f})",
        "serviços 6–9 (p.p.)": ss.contrib_servicos_pp,
        "share dos serviços (%)": ss.share_pct,
        "SGS 10844 12m (%)": _serv12(ano),
        "resíduo (p.p.)": d.residuo_pp.iloc[0],
    })
display(pd.DataFrame(linhas))"""

c_contrib_fig = r"""\
anos = [2021, 2022, 2023, 2024, 2025, 2026]
piv = (c[c.ano.isin(anos)]
       .pivot(index="ano", columns="grupo", values="contribuicao_pp")
       .reindex(anos))
ordem = piv.sum().sort_values(ascending=False).index
piv = piv[ordem]
cores = [AZUL, VERMELHO, VERDE, LARANJA, ROXO, MARROM, CINZA,
         "#bcbd22", "#17becf"]
fig, ax = plt.subplots(figsize=(11, 5.5))
left = np.zeros(len(piv))
for grupo, cor in zip(piv.columns, cores):
    ax.barh(piv.index.astype(str), piv[grupo], left=left, color=cor,
            label=grupo)
    left = left + piv[grupo].fillna(0).values
for i, ano in enumerate(piv.index):
    total = c[c.ano == ano].total_ipca_12m.iloc[0]
    ax.text(left[i] + 0.08, i, f"soma {left[i]:.2f} | IPCA {total:.2f}",
            va="center", fontsize=8)
ax.set_xlabel("contribuição (p.p.)")
ax.set_title("Contribuição por grupo para o IPCA 12m — soma aproximada")
ax.legend(fontsize=7, ncol=3, loc="upper center",
          bbox_to_anchor=(0.5, -0.12))
ax.margins(x=0.18)
salvar(fig, "09_contribuicoes")"""

c_phillips = r"""\
ph = j.phillips()
cols = ["modelo", "coef", "erro_padrao", "p_valor", "r2", "n", "janela"]
print("Amostra 2012–2026")
display(ph[ph.variavel == "u"][cols].rename(columns={
    "modelo": "modelo", "coef": "coef. u", "erro_padrao": "erro-padrão",
    "p_valor": "p", "r2": "R²", "n": "n", "janela": "janela"}))
print("Amostra 2021–2026")
phr = j.phillips(("2021-01", "2026-09"))
display(phr[phr.variavel == "u"][cols].rename(columns={
    "modelo": "modelo", "coef": "coef. u", "erro_padrao": "erro-padrão",
    "p_valor": "p", "r2": "R²", "n": "n", "janela": "janela"}))"""

c_phillips_fig = r"""\
b = j.base_phillips().copy()
b.index = b.index.to_timestamp(how="end")
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, y, titulo in ((axes[0], "ipca12", "IPCA cheio"),
                      (axes[1], "serv12", "Serviços")):
    pre = b[b.index < "2020-01-01"]
    mid = b[(b.index >= "2020-01-01") & (b.index < "2021-01-01")]
    pos = b[b.index >= "2021-01-01"]
    ax.scatter(pre["u"], pre[y], s=14, color=AZUL, alpha=0.55,
               label="2012–2019")
    ax.scatter(mid["u"], mid[y], s=14, color=CINZA, alpha=0.55, label="2020")
    ax.scatter(pos["u"], pos[y], s=14, color=VERMELHO, alpha=0.55,
               label="2021–2026")
    coef = np.polyfit(b["u"], b[y], 1)
    xs = np.linspace(b["u"].min(), b["u"].max(), 60)
    ax.plot(xs, np.polyval(coef, xs), color="black", lw=1.5,
            label="ajuste linear (amostra toda)")
    ax.set_xlabel("desemprego (%)")
    ax.set_ylabel(f"{titulo} 12m (%)")
    ax.set_title(f"{titulo} × desemprego — associação, não causalidade")
    ax.legend(fontsize=8)
fig.tight_layout()
salvar(fig, "09_phillips")"""

c_prod = r"""\
t = j.produtividade_anual()
cols = ["ano", "sal_yoy_pct", "prod_yoy_pct", "ulc_pp", "razao_sal_prod",
        "ipca_dez_pct", "servicos_dez_pct", "desemprego_medio_pct"]
display(t[(t.ano >= 2012) & (t.ano <= 2025)][cols].rename(columns={
    "ano": "ano",
    "sal_yoy_pct": "salário real (%)",
    "prod_yoy_pct": "produtividade (%)",
    "ulc_pp": "ULC (p.p.)",
    "razao_sal_prod": "razão salário/prod.",
    "ipca_dez_pct": "IPCA dez (%)",
    "servicos_dez_pct": "serviços dez (%)",
    "desemprego_medio_pct": "desemprego médio (%)",
}))
print("2012 é o ano-base (sem variação); 2026 ainda incompleto.")"""

c_prod_fig = r"""\
tt = t[t.ano <= 2025]
tu = t[t.ulc_pp.notna()]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(tt.ano, tt.sal_idx, color=VERMELHO, marker="o", lw=2,
         label="salário real")
ax1.plot(tt.ano, tt.prod_idx, color=AZUL, marker="o", lw=2,
         label="produtividade por trabalhador")
ax1.axhline(100, color=CINZA, lw=0.8)
ax1.set_title("2012 = 100: salário real × produtividade")
ax1.set_ylabel("índice")
ax1.legend(fontsize=9)
ax2.bar(tu.ano, tu.ulc_pp,
        color=[VERMELHO if v > 0 else AZUL for v in tu.ulc_pp])
ax2.axhline(0, color="k", lw=1)
ax2.set_title("ULC (salário real − produtividade, p.p.)")
ax2.set_ylabel("p.p.")
for ax in (ax1, ax2):
    ax.margins(x=0.03)
fig.tight_layout()
salvar(fig, "09_produtividade")"""

c_trabalho = r"""\
mt = j.mercado_trabalho_resumo()
display(mt.rename(columns={
    "indicador": "indicador",
    "ultimo": "último",
    "data_ultimo": "data",
    "media_2012_2019": "média 2012–19",
    "media_2025_2026": "média 2025–26",
    "minimo": "mínimo",
    "data_minimo": "data do mínimo",
    "maximo": "máximo",
    "data_maximo": "data do máximo",
}))"""

c_trabalho_fig = r"""\
mtw = pd.read_parquet(p / "dados" / "processado" / "mercado_trabalho.parquet")
piv = mtw.pivot(index="data", columns="variavel", values="valor").sort_index()
des = pd.read_parquet(p / "dados" / "processado" / "desemprego.parquet")
u = (des.assign(data=lambda d: pd.to_datetime(d["data"]))
     .set_index("data")["taxa_pct"].sort_index())

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(u.index, u.values, color=AZUL, lw=1.1, label="desemprego (mensal)")
ax1.axhline(u[u.index.year <= 2019].mean(), color=CINZA, ls="--", lw=1.2,
            label="média 2012–19")
ax1.set_title("Desemprego: mínimo da série em 2025–26")
ax1.set_ylabel("%")
ax1.legend(fontsize=9)
ax2.plot(piv.index, piv["nivel_ocupacao_pct"], color=VERDE, lw=2,
         label="nível de ocupação")
ax2.plot(piv.index, piv["participacao_pct"], color=LARANJA, lw=2,
         label="participação")
ax2.plot(piv.index, piv["informalidade_pct"], color=ROXO, lw=2,
         label="informalidade")
ax2.set_title("Ocupação em recorde; participação abaixo de 2012–19")
ax2.set_ylabel("%")
ax2.legend(fontsize=9)
fig.tight_layout()
salvar(fig, "09_trabalho")"""

c_focus = r"""\
e = j.expectativas_anuais()
display(e.rename(columns={
    "data_pesquisa": "pesquisa",
    "data_referencia": "ano",
    "media": "média (%)",
    "mediana": "mediana (%)",
    "desvio_padrao": "desvio-padrão (p.p.)",
    "meta_pct": "meta (%)",
    "teto_pct": "teto (%)",
    "acima_meta": "acima da meta?",
    "acima_teto": "acima do teto?",
}))
cred = j.credibilidade().rename(columns={
    "periodo": "período",
    "meses": "meses",
    "focus_12m_medio_pct": "Focus 12m médio (%)",
    "meta_media_pct": "meta média (%)",
    "gap_medio_pp": "gap médio (p.p.)",
    "dispersao_media_pp": "dispersão média (p.p.)",
    "pct_meses_acima_meta": "% meses acima da meta",
    "pct_meses_acima_teto": "% meses acima do teto",
})
display(cred.style.format({
    "meses": "{:.0f}",
    "Focus 12m médio (%)": "{:.3f}",
    "meta média (%)": "{:.2f}",
    "gap médio (p.p.)": "{:.2f}",
    "dispersão média (p.p.)": "{:.2f}",
    "% meses acima da meta": "{:.2f}",
    "% meses acima do teto": "{:.2f}",
}))"""

c_focus_fig = r"""\
foc = pd.read_parquet(p / "dados" / "processado" / "focus_inflacao12m.parquet")
foc = foc[(foc.suavizada == "N") & (foc.base_calculo == 0)].copy()
foc["data_pesquisa"] = pd.to_datetime(foc["data_pesquisa"])
foc = foc.sort_values("data_pesquisa")
foc["mes"] = foc["data_pesquisa"].dt.to_period("M")
fm = foc.groupby("mes").tail(1).set_index("mes").sort_index()
fm.index = fm.index.to_timestamp(how="end")
fm = fm[fm.index >= "2012-01-01"]

meta_m = pd.Series([j.METAS_ANUAIS[a][0] for a in fm.index.year],
                   index=fm.index)
tol_m = pd.Series([j.METAS_ANUAIS[a][1] for a in fm.index.year],
                  index=fm.index)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(fm.index, fm["media"], color=AZUL, lw=1.5, label="Focus 12m")
ax1.plot(meta_m.index, meta_m, color=VERMELHO, ls="--", lw=1.2,
         label="meta em vigor")
ax1.plot(meta_m.index, meta_m + tol_m, color=LARANJA, ls=":", lw=1.2,
         label="teto")
ax1.set_title("Expectativa de IPCA 12m (base 0, não suavizada)")
ax1.set_ylabel("%")
ax1.legend(fontsize=9)
ax2.plot(fm.index, fm["desvio_padrao"], color=ROXO, lw=1.2)
ax2.set_title("Dispersão das expectativas (desvio-padrão, p.p.)")
ax2.set_ylabel("p.p.")
fig.tight_layout()
salvar(fig, "09_focus")"""

c_citacoes = r"""\
cit = j.citacoes_atas()
display(cit[["num", "data", "tema", "trecho", "verbatim_ok"]])
display(j.termo_por_ata())
for r in cit.itertuples():
    print(f"\nAta {r.num} ({r.data}) — {r.tema}:")
    print(textwrap.fill(f"“{r.trecho}”", width=100,
                        initial_indent="  ", subsequent_indent="  "))"""

c_veredito = r"""\
v = j.veredito()
with pd.option_context("display.max_colwidth", None):
    display(v[["justificativa_bc", "dado", "leitura", "veredito"]].rename(
        columns={
            "justificativa_bc": "o que o BC diz",
            "dado": "o que os dados mostram",
            "leitura": "leitura",
            "veredito": "veredito",
        }))"""

md_achados = """\
**Achados verificáveis.**

1. **A inflação acima da meta é fato — mas o juro alto não a entregou.**
   Com as metas efetivas, o IPCA furou o teto em **2015, 2021, 2022, 2024**
   e em **2026** (parcial); ficou dentro em 2012–14, 2016, 2018–20, 2023 e
   2025, e **abaixo do piso em 2017**. Desde 2021, foram **3 anos fechados
   acima do teto em 5** (2021, 2022, 2024), e o 12m de out/26 (4,63%) segue
   acima de 4,50%. Isso não prova que o juro alto "falhou" — faltam
   contrafactual e choques externos —, mas também não mostra que ele
   entregou a meta.

2. **A composição do IPCA não é a de uma economia "superaquecida" por
   salários.** Em 2021, transportes (4,61 p.p.) e habitação (2,11 p.p.)
   explicam a maior parte; em 2022, alimentação (2,54) e saúde (1,48); em
   2024, alimentação (1,66) e saúde (0,82); em 2026, alimentação (1,23) e
   saúde (0,74). O proxy de serviços (grupos 6–9) responde por 11,5% do IPCA
   em 2021 e 39–46% em 2022–26 — não é o motor principal em 2021. A série
   oficial de serviços (SGS 10844) está na tabela ao lado do proxy.

3. **A curva de Phillips não aparece no IPCA cheio.** Na amostra 2012–26,
   o coeficiente do desemprego é −0,05 (p=0,73, R²=0,00); com Focus e câmbio,
   +0,20 (p=0,08). Para serviços, o sinal é negativo e significativo (−0,50,
   p=0,001; com controles, −0,31, p=0,001). Em 2021–26, o IPCA cheio tem
   sinal **positivo** (+0,53, p=0,01). Isso é associação condicional, não
   causalidade: a desinflação de 2022–26 ocorreu com o desemprego caindo de
   9,5% (média de 2022) para 5,2% (set/26).

4. **Salário acima da produtividade: procede em parte.** Salário real
   +15,5% contra produtividade +0,6% entre 2012 e 2025 (razão 1,15); a ULC
   foi positiva em 2023–25 (+5,3, +3,1, +5,2 p.p.). Mas o salário real caiu
   8,4% entre 2020 e 2022, e a produtividade é por trabalhador, não por
   hora; o gap acumulado é compatível com recuperação, não com espiral.

5. **Mercado de trabalho apertado: descrição procede, prova de pressão não.**
   Desemprego 5,2% (mínimo 5,1% em dez/25), ocupação 59,0% (recorde),
   informalidade 37,5% (abaixo de 39,9% em 2012–19) — mas participação 62,2%,
   abaixo de 62,8% em 2012–19. Parte do aperto vem de menor oferta de
   trabalho. E o mercado apertado não se traduz automaticamente em IPCA
   cheio (ver item 3).

6. **Expectativas desancoradas: diagnóstico procede; causa não identificada.**
   Focus de 13/11/2026: 2026 5,11%, 2027 4,96%, 2028 4,05%, 2029 3,89%,
   2030 3,86%; 12m 5,15%. O nível médio do Focus 12m **caiu** de 5,24%
   (2012–19) para 4,63% (2021–26), mas a meta média caiu mais (4,47% →
   3,25%): o **gap à meta subiu de 0,77 para 1,38 p.p.** e a fração de meses
   acima do teto **triplicou** (11,5% → 39,4%). Em 2021–26, a expectativa
   ficou acima da meta em vigor em 98,6% dos meses. O Focus é expectativa de
   mercado, não medida de credibilidade, e não diz *por que* está
   desancorado.

7. **As atas confirmam o deslocamento para a oferta.** As atas 280 (05/08/26)
   e 281 (16/09/26) dizem "mercado de trabalho aquecido"; a 282 (04/11/26)
   lista **quatro choques de oferta** (petróleo, El Niño, fim da escala 6X1,
   câmbio) e fala em "expectativas desancoradas", sem repetir "aquecido".

**Limites declarados.** Não há identificação causal: a Phillips é
correlação condicional; a decomposição é contábil (soma dos grupos ≈ IPCA,
resíduo ≤ 0,36 p.p.); a produtividade é por trabalhador (a PNAD agregada não
publica horas no SIDRA); o proxy de serviços (grupos 6–9) não é a série
oficial SGS 10844; 2026 está incompleto (IPCA até out, PNAD até o 3º tri);
o Focus é expectativa de mercado, não credibilidade do BC. Onde a série não
permite separar os mecanismos, a leitura é "não verificável", não "falsa"."""

nb.cells = [
    nbf.v4.new_markdown_cell(md_intro),
    nbf.v4.new_code_cell(c_imports),
    nbf.v4.new_markdown_cell(
        "## 1 · Metas efetivas, faixa de tolerância e IPCA realizado\n\n"
        "A meta não foi 4,5% o tempo todo: ela caiu para 4,25% em 2019, "
        "4,00% em 2020, 3,75% em 2021, 3,50% em 2022, 3,25% em 2023 e 3,00% "
        "em 2024–26. A tolerância também mudou (±2,0 p.p. até 2016; ±1,5 "
        "depois). Comparar o IPCA com uma meta fixa de 4,5% esconde os anos "
        "em que a meta era mais baixa."),
    nbf.v4.new_code_cell(c_metas),
    nbf.v4.new_code_cell(c_metas_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_metas.png` — a linha azul é o IPCA 12m; "
        "a faixa cinza é a tolerância do ano; os pontos de dezembro são "
        "coloridos pelo veredito (vermelho acima do teto, laranja abaixo do "
        "piso, verde dentro)."),
    nbf.v4.new_markdown_cell(
        "## 2 · O que compõe o IPCA: grupos, não só salário\n\n"
        "A contribuição é `variação 12m do grupo × peso do mês`, uma "
        "aproximação padrão. A soma dos 9 grupos difere do IPCA cheio em até "
        "0,36 p.p. (peso muda ao longo dos 12 meses); o resíduo está na "
        "tabela. O proxy de **serviços** (grupos 6–9: saúde, despesas "
        "pessoais, educação, comunicação) **não** é a série oficial de "
        "serviços do BCB (SGS 10844) — as duas aparecem lado a lado."),
    nbf.v4.new_code_cell(c_contrib),
    nbf.v4.new_code_cell(c_contrib_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_contribuicoes.png` — barras empilhadas "
        "por grupo; o texto à direita mostra a soma das contribuições e o "
        "IPCA cheio. 2026 = 12m até out/26."),
    nbf.v4.new_markdown_cell(
        "## 3 · Phillips: desemprego e inflação, associação condicional\n\n"
        "Modelos OLS com erro-padrão HAC (12 lags). A variável dependente é "
        "o IPCA 12m (ou serviços 12m); a explicativa de interesse é o "
        "desemprego. Focus 12m e câmbio 12m entram como controles. **Sinal "
        "negativo** é o previsto pela curva de Phillips; **positivo** é o "
        "oposto. Nenhum modelo identifica causalidade."),
    nbf.v4.new_code_cell(c_phillips),
    nbf.v4.new_code_cell(c_phillips_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_phillips.png` — cada ponto é um mês; a "
        "linha preta é o ajuste linear da amostra toda. O contraste visual "
        "entre 2012–19 (azul) e 2021–26 (vermelho) mostra por que o sinal "
        "do IPCA cheio se inverte no período recente."),
    nbf.v4.new_markdown_cell(
        "## 4 · Salário real, produtividade e ULC\n\n"
        "Produtividade = PIB volume (CNT) ÷ pessoas ocupadas (PNAD), média "
        "anual. É produtividade **por trabalhador**, não por hora. ULC = "
        "variação do salário real − variação da produtividade (proxy; não é "
        "a ULC oficial do IBGE)."),
    nbf.v4.new_code_cell(c_prod),
    nbf.v4.new_code_cell(c_prod_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_produtividade.png` — à esquerda, os "
        "índices (2012=100); à direita, a ULC anual. O salário real só "
        "recupera o nível de 2012 em 2023 e o gap acumulado chega a 15% em "
        "2025."),
    nbf.v4.new_markdown_cell(
        "## 5 · Mercado de trabalho: apertado, mas com menos oferta\n\n"
        "Desemprego mensal (PNAD, 3 meses móveis) e indicadores trimestrais "
        "(ocupação, participação, informalidade). A informalidade só é "
        "publicada a partir de 2015Q4."),
    nbf.v4.new_code_cell(c_trabalho),
    nbf.v4.new_code_cell(c_trabalho_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_trabalho.png` — à esquerda, o desemprego "
        "contra a média de 2012–19; à direita, ocupação, participação e "
        "informalidade. A ocupação está em recorde; a participação está "
        "abaixo da média histórica."),
    nbf.v4.new_markdown_cell(
        "## 6 · Expectativas: Focus 12m e a meta em vigor\n\n"
        "Série não suavizada e **base de cálculo 0** (a base 1 coexiste "
        "desde 2014 e não pode ser misturada). A comparação de credibilidade "
        "usa a meta efetiva de cada ano — não a meta de 3% atual, que só "
        "vale desde 2025."),
    nbf.v4.new_code_cell(c_focus),
    nbf.v4.new_code_cell(c_focus_fig),
    nbf.v4.new_markdown_cell(
        "**Figura:** `viz/figs/09_focus.png` — à esquerda, o Focus 12m "
        "contra a meta e o teto em vigor; à direita, a dispersão "
        "(desvio-padrão) das expectativas."),
    nbf.v4.new_markdown_cell(
        "## 7 · O que as atas dizem (citação verbatim)\n\n"
        "As citações são comparadas com o texto bruto das atas; "
        "`verbatim_ok=True` significa que a frase aparece exatamente no "
        "arquivo. Artefatos de OCR do texto bruto (por exemplo, `El Niño ,`) "
        "são preservados na citação."),
    nbf.v4.new_code_cell(c_citacoes),
    nbf.v4.new_markdown_cell(
        "## 8 · O que o BC diz / o que os dados mostram\n\n"
        "Tabela gerada por `justificativas.veredito()`: cada linha contrasta "
        "a justificativa com o dado e com a leitura possível. Os números são "
        "calculados nas células anteriores, não digitados à mão."),
    nbf.v4.new_code_cell(c_veredito),
    nbf.v4.new_markdown_cell(md_achados),
]

destino = (Path(__file__).resolve().parents[1] / "notebooks"
           / "09_justificativas.ipynb")
nbf.write(nb, destino)
print("ok ->", destino)
