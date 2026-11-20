"""Páginas do app — o conteúdo de cada item do menu lateral.

Uma função por página; a orquestração (sidebar + dispatch) fica em
`app/app.py`. Nenhuma leitura de dado aqui: tudo entra por `d`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.dados import ANO_CORTE  # noqa: E402
from app.graficos import (  # noqa: E402
    fig_cascata, fig_detentores, fig_desvio_taylor, fig_estoque_detentor,
    fig_fluxo_juros_detentor, fig_fluxos_anuais, fig_juro_real,
    fig_juros_primario, fig_juros_swaps, fig_selic_inflacao)
from app.tabelas import (  # noqa: E402
    df_mandatos, fig_i_g, fmt_bi, fmt_pct, resumo)


def visao_geral(d) -> None:
    r = resumo(d)
    st.title("Visão geral")
    st.markdown(
        "Uma base de dados própria, construída de **fontes primárias "
        "(BCB/SGS, Tesouro/RMD, Focus/Olinda, IBGE/SIDRA)**, validada "
        "externamente e organizada para responder as cinco perguntas "
        "desta pesquisa — ver a aba **Fontes e metodologia**."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Juros nominais {r['ultimo_ano_completo']}",
              fmt_bi(r["row"].juros_mi / 1000),
              f"{fmt_pct(r['row'].juros_pib_pct)} do PIB")
    c2.metric("Efeito swaps", f"{r['row'].swap_pp_pib:+.2f} p.p.",
              "aumenta" if r["row"].swap_pp_pib > 0 else "reduz")
    c3.metric("Custo médio DPF", f"{r['cm_val']:.2f}% a.a.".replace(".", ","),
              f"dez/20: {r['cm_ult']:%m/%Y}")
    c4.metric("Estoque DPMFi", fmt_bi(
        d["detentores"][d["detentores"].data == r["dez_ult"]].valor_bi.sum(), 0))

    st.plotly_chart(fig_juros_swaps(d), width="stretch")
    st.markdown(
        "**Validação BNDES** — o cálculo próprio reproduz o Estudo BNDES 67/2026 "
        "com desvio ≤ 0,03 p.p. (ver notebook 00 ou a tabela na parte inferior):"
    )
    st.dataframe(d["validacao_bndes"], width="stretch", hide_index=True)


def p1(d) -> None:
    st.title("P1 · Os juros altos se justificam?")
    st.markdown(
        "A Selic acompanha a inflação **esperada** (Focus), não realizada. O "
        "que é excepcional é a magnitude: juro real ex ante de 2024–2026 em "
        "média ~8,8 p.p. (6,9 em 2024 → 10,1 em 2026), com inflação "
        "**dentro da meta**."
    )
    st.plotly_chart(fig_selic_inflacao(d), width="stretch")
    st.plotly_chart(fig_juro_real(d), width="stretch")
    st.plotly_chart(fig_desvio_taylor(d), width="stretch")
    st.info(
        "**Conclusão verificável:** o juro extra atual não é “preço da "
        "inflação”: é um prêmio institucional adicional. Defender que "
        "“está justificado” é uma posição — a causa adicional (risco fiscal? "
        "credibilidade?) não está nos dados macro aqui usados."
    )


def p2(d) -> None:
    st.title("P2 · Quem recebe os juros?")
    st.markdown(
        "Composição de estoque por grupo de detentor (RMD 2.7) e **estimativa** "
        "do fluxo de juros por grupo (juros do ano × participação em dezembro)."
    )
    st.plotly_chart(fig_detentores(d, stacked=True), width="stretch")
    cols = st.columns(2)
    with cols[0]:
        st.plotly_chart(fig_estoque_detentor(d), width="stretch")
    with cols[1]:
        st.plotly_chart(fig_fluxo_juros_detentor(d), width="stretch")
    st.warning(
        "**Estimativa, não dado oficial:** participação em dezembro × juros "
        "anuais. A União não publica fluxo por credor. Identificar "
        "instituições dentro do grupo não é possível (sigilo; Req. 696/2019 "
        "negado) — ver aba **Transparência: lacunas**."
    )


def p3(d) -> None:
    st.title("P3 · Os juros amortizam a dívida?")
    st.markdown(
        "Identidade dos fatores de variação da DPF (Tesouro, anexo 2.9): "
        "variação do estoque = emissão líquida + juros — em 2025, R$ 439 bi "
        "+ R$ 880 bi = R$ 1.319 bi (67% do aumento foram juros). Os juros "
        "**não amortizam** a dívida; **são a dívida nova**."
    )
    f_ano = st.slider("ano da cascata", 2012, 2025, 2025, key="cascata")
    st.plotly_chart(fig_cascata(d, f_ano), width="stretch")
    st.plotly_chart(fig_fluxos_anuais(d), width="stretch")
    t = d["fatores"].copy()
    t = t[(t.ano >= 2012) & (t.ano < ANO_CORTE)]
    t["emissoes_mult_juros"] = t.emissoes_mi / t.juros_apropriados_mi
    st.dataframe(
        t[["ano", "emissoes_mi", "resgates_mi", "juros_apropriados_mi",
           "emissoes_mult_juros"]].assign(
            **{"emissoes (R$ bi)": lambda x: (x.emissoes_mi / 1000).round(0),
               "resgates (R$ bi)": lambda x: (x.resgates_mi / -1000).round(0),
               "juros (R$ bi)": lambda x: (x.juros_apropriados_mi / 1000).round(0)}
        )[["ano", "emissoes (R$ bi)", "resgates (R$ bi)", "juros (R$ bi)",
           "emissoes_mult_juros"]].round(2),
        width="stretch", hide_index=True,
    )
    st.plotly_chart(fig_juros_primario(d), width="stretch")
    st.info("Equação honesta para o público: **os juros não reduzem a dívida — "
            "eles são a dívida nova** (mais a dívida que chega próxima).")


def p4(d) -> None:
    st.title("P4 · Os juros geram capital produtivo?")
    st.markdown(
        "**i > g quase sempre desde 2012** (exceção: choque inflacionário de "
        "2021–22) e **r > g real desde 2022**: a dívida se auto-alimenta e o "
        "capital migra do crédito/investimento para o título soberano."
    )
    tab, fig = fig_i_g(d)
    c1, c2 = st.columns([2, 3])
    with c1:
        st.dataframe(tab.round(1), width="stretch")
    with c2:
        st.plotly_chart(fig, width="stretch")
    st.info(
        "Nos dados públicos de fluxo **não há caminho pelo qual o dispêndio "
        "de juros se converta em investimento produtivo**: é rolagem (P3) + "
        "transferência a detentores (P2). O soberano rendendo juro real alto "
        "sem risco “rouba” a poupança do crédito privado."
    )


def p5(d) -> None:
    r = resumo(d)
    j = d["juros"]
    st.title("P5 · O aumento foi proposital?")
    st.markdown(
        "O que os dados mostram: a régua de juro real **alternou de forma "
        "dramática e reversível** entre mandatos — não é fatalidade técnica. "
        "**Não é afirmação de intenção**: isso exige documentos (atas, "
        "manifestos, ofícios) — fase posterior."
    )
    tab = df_mandatos(d)
    st.bar_chart(tab["juro_real_ex_ante_medio"], color="#1f77b4", height=340)
    st.dataframe(tab.round(1), width="stretch")

    j2 = j[j.ano >= 2002]
    st.caption(
        f"Dispêndio nominal com juros: {fmt_bi(j2.juros_mi.iloc[0] / 1000, 0)} "
        f"({j2.ano.iloc[0]}) → {fmt_bi(j2[j2.ano < ANO_CORTE].juros_mi.iloc[-1] / 1000, 0)} "
        f"({r['ultimo_ano_completo']}) — sem contar o efeito dos swaps."
    )
    st.plotly_chart(fig_juros_swaps(d), width="stretch")
    st.info(
        "Em **2021** o juro real ex ante foi **−0,3%** (média 2019–22: 2,1%) "
        "e em **2025** foi **9,6%**, sem mudança da estrutura produtiva: o "
        "patamar é *escolha de política*. Quem defende que “não havia "
        "alternativa” precisa apontar por que ela praticamente inverteu "
        "de 2022 para cá."
    )


def transparencia() -> None:
    st.title("O que NÃO é público (e por quê)")
    st.markdown(
        "Esta ferramenta mostra tudo que é possível mostrar com dados "
        "públicos — e **declara explicitamente** o que não é público:"
    )
    lacunas = [
        {
            "lacuna": "Quem (nome/instituição) recebe quanto de juros",
            "estado": "**Negado.** Requerimento 696/2019 (Câmara dos "
                      "Deputados) pedia a lista ao STN; resposta foi "
                      "negativa por **sigilo bancário**.",
            "o que há": "Estimativa por grupo: participação de dezembro × "
                        "juros nominais anuais (aba P2).",
        },
        {
            "lacuna": "Fluxo de juros por detentor (dado oficial)",
            "estado": "**Não existe.** O Tesouro publica juros agregados "
                      "(SGS 4616); por detentor só o estoque "
                      "(RMD 2.7), mensal, por grupo.",
            "o que há": "Estimativa própria — marcada como tal em toda "
                        "a interface.",
        },
        {
            "lacuna": "Desemprego 2002–2011 (série comparável)",
            "estado": "**Não existe.** A PNAD-C começou em 2012; antes só "
                      "PNAD anual/mensal incomparável.",
            "o que há": "Série desde 2012, com a lacuna informada nos "
                        "gráficos que a usam.",
        },
        {
            "lacuna": "API do Portal da Transparência",
            "estado": "**Exige chave de API** (o pedido via LAI foi "
                      "cancelado/deferido com exigência de credencial); "
                      "dispensada neste projeto — substituída por SGS 4616 "
                      "+ fatores de variação da DPF.",
            "o que há": "Mesmo resultado analítico pelas séries do BCB/Tesouro.",
        },
        {
            "lacuna": "Contratos de swap por contraparte",
            "estado": "**Agregado**. O BCB publica o resultado caixa total "
                      "(SGS 29522), não o desmembrado por banco.",
            "o que há": "A contribuição anual dos swaps para os juros "
                        "(p.p. do PIB) — ver Visão geral.",
        },
    ]
    for l in lacunas:
        with st.expander(f"🔒 {l['lacuna']}"):
            st.markdown(f"**Estado atual:** {l['estado']}")
            st.markdown(f"**O que a ferramenta oferece no lugar:** {l['o que há']}")
    st.success(
        "Para abrir de fato a identificação dos credores, seria necessário "
        "um ato legal/regulatório sobre titularidade junto aos custodiantes "
        "(SELIC/Cetip) — a ferramenta indica isto como caminho, não como "
        "afirmação."
    )


def fontes() -> None:
    st.title("Fontes e metodologia")
    st.markdown(f"""
| Fonte | Uso nesta ferramenta |
| --- | --- |
| **BCB/SGS** (25 séries) | juros nominais (4616), swaps caixa (29522), PIB nominal (4380), Selic/IPCA, primário |
| **Tesouro/STN — RMD** | detentores (Anexo 2.7), custo médio (4.1–4.3), composição (5.5) |
| **Tesouro/STN — fatores DPF (Anexo 2.9)** | estoque, emissões, resgates, juros apropriados |
| **Focus / Olinda (BCB)** | IPCA-12m e Selic anuais (medianas) |
| **IBGE SIDRA 6381** | desemprego PNAD-C (desde 2012) |
| **BNDES Estudo 67/2026** | referência externa de validação |

**Regras declaradas:**

1. **Fluxo de juros por detentor é estimativa** (participação dez × juros
   anuais) — não dado oficial.
2. **Nomes de credores não são públicos** (Req. 696/2019 negado por sigilo).
3. **Desemprego** só a partir de 2012 — lacuna informada, não escondida.
4. **{ANO_CORTE} é ano incompleto** nas séries de fluxo — o app o exclui dos
   gráficos anuais fechados e avisa.
5. Swaps: `juros_ex_swap = juros + resultado_caixa` (prejuízo do BCB aumenta
   juros; ganho reduz) — validado contra BNDES 67/2026 (desvio ≤ 0,03 p.p.).

**Notebooks completos:** `notebooks/00_validacao.ipynb` …
`05_proposital.ipynb` (executados, com saída). O núcleo analítico é
`src/processa/indicadores.py`; os extratores (com cache) em `src/extratores/`.
""")
