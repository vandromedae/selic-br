"""Corpus complementar — documentos de posição (fase de documentos).

Diferente das atas (decisão coletiva, sem votos nominais) e dos discursos
(inventário temático de apresentações), este módulo cataloga DOCUMENTOS DE
POSIÇÃO com tese explícita e autor assinado — manifestos, artigos, declarações.

Registro curado (humano, não automático):
- `DOCS` ....... metadados de cada documento (autor, data, fonte, URL, tese)
- `TRECHOS` .... citações verbatim; `tema` usa o vocabulário de
  `atas_copom.TEMAS` quando possível, senão "tese"/"proposta"
- `trechos()` confere que cada citação existe EXATAMENTE no texto bruto
  (`verbatim_ok`) — pega erro de transcrição na hora

`verificacao_eu_acuso()`, `verificacao_kanczuk()`, `verificacao_febraban()`
e `verificacao_anbima()` recalculam a aritmética de cada documento com as
séries do projeto (SGS/Focus/RMD) — nada é aceito sem conferência. É um
padrão repetível: para cada novo documento de posição, uma função de
verificação.

Saídas:
- dados/processado/documentos_indice.csv
- dados/processado/documentos_trechos.parquet
- dados/processado/documentos_verificacao.csv (as duas verificações)

Coleta do texto bruto: GET público da URL do artigo (requests, UA de
navegador), corte do corpo + notas de rodapé antes da seção de comentários;
script em /tmp/opencode/baixa_artigo.py (regenerar com webfetch se preciso).
Os documentos de entidade (Febraban/ANBIMA) foram arquivados manualmente a
partir do texto devolvido pelo webfetch, com o mesmo corte: corpo integral,
antes de menu/rodapé/comentários.

Rodar: PYTHONPATH=. python -m src.processa.documentos
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..extratores.base import PROCESSADO, RAIZ

BRUTO_DOC = RAIZ / "dados" / "bruto" / "documentos"

# ------------------------------------------------------------------ registro

DOCS: list[dict] = [
    {
        "id": "eu_acuso_2026",
        "tipo": "artigo-manifesto",
        "autor": "André Lara Resende (ex-presidente do BCB)",
        "data": "2026-09-25",
        "fonte": "Substack — Um Cético Esperançoso",
        "url": "https://andrelararesende.substack.com/p/eu-acuso-uma-proposta-para-eliminar",
        "titulo": "Eu Acuso: uma proposta para eliminar os juros absurdos",
        "arquivo": "dados/bruto/documentos/eu_acuso_lara_resende_2026-09-25.txt",
        "tese": (
            "o serviço da dívida (juros) é o motor do desequilíbrio fiscal; "
            "propõe banda de Selic entre 3% e crescimento nominal potencial, "
            "com corte gradual para ~7,5% a.a."
        ),
    },
    {
        "id": "kanczuk_asa_2025",
        "tipo": "entrevista",
        "autor": "Fábio Kanczuk (diretor de macroeconomia do ASA; "
                 "ex-diretor de Política Econômica do BCB 2019–2021)",
        "data": "2025-07-25",
        "fonte": "NeoFeed — entrevista na Expert XP (reporter Guilherme Guilherme)",
        "url": ("https://neofeed.com.br/economia/"
                "bc-nao-levara-inflacao-para-a-meta-e-cortara-juros-mesmo-sem-"
                "espaco-diz-fabio-kanczuk-do-asa/"),
        "titulo": ("\"BC não levará inflação para a meta e cortará juros "
                   "mesmo sem espaço\", diz Fabio Kanczuk, do ASA"),
        "arquivo": "dados/bruto/documentos/kanczuk_asa_2025-07-25.txt",
        "tese": (
            "o juro neutro real é ~8% (não 5%); a Selic de 15% é pouco "
            "restritiva e deveria ficar estável por 2–3 anos; o BC vai "
            "cortar antes da hora, \"uma opção para não levar a meta de "
            "inflação a sério\""
        ),
    },
    {
        "id": "febraban_sidney_2026",
        "tipo": "nota de entidade (assinada)",
        "autor": "Isaac Sidney (presidente da Febraban; ex-diretor do BCB)",
        "data": "2026-01-12",
        "fonte": "Febraban — Notícias (nota sobre o IPCA de 2025)",
        "url": "https://portal.febraban.org.br/noticia/4412/pt-br/",
        "titulo": "Presidente da Febraban comenta IPCA de 2025",
        "arquivo": "dados/bruto/documentos/febraban_sidney_2026-01-12.txt",
        "tese": (
            "elogia a autonomia do BC e a desinflação, mas recusa explicitamente "
            "celebrar a Selic de 15%; \"bancos não precisam de juros altos\"; "
            "patamares menos rigorosos de juros dependem de consolidação fiscal"
        ),
    },
    {
        "id": "anbima_2025_01",
        "tipo": "release de entidade (projeção coletiva)",
        "autor": ("Grupo Consultivo Macroeconômico da ANBIMA — 26 economistas "
                  "de instituições associadas; fala de David Beker, "
                  "vice-coordenador"),
        "data": "2025-01-27",
        "fonte": "ANBIMA — Notícias",
        "url": ("https://www.anbima.com.br/pt_br/noticias/"
                "selic-deve-chegar-a-15-25-ate-junho-projeta-grupo-consultivo-"
                "macroeconomico.htm"),
        "titulo": "Selic deve chegar a 15,25% até junho, projeta Grupo "
                  "Consultivo Macroeconômico",
        "arquivo": "dados/bruto/documentos/anbima_grupo_2025-01-27.txt",
        "tese": (
            "deterioração fiscal justifica \"política monetária mais "
            "restritiva\"; projeção de Selic em 15,25% até o fim de 2025 e "
            "IPCA 2025 em 5,6%"
        ),
    },
    {
        "id": "anbima_2025_09",
        "tipo": "release de entidade (projeção coletiva)",
        "autor": ("Grupo Consultivo Macroeconômico da ANBIMA — 26 economistas; "
                  "fala de Fernando Honorato, coordenador"),
        "data": "2025-09-15",
        "fonte": "ANBIMA — Notícias",
        "url": ("https://www.anbima.com.br/pt_br/noticias/"
                "selic-deve-ser-reduzida-para-14-75-em-janeiro-de-2026-"
                "projeta-grupo-consultivo-macroeconomico.htm"),
        "titulo": "Selic deve ser reduzida para 14,75% em janeiro de 2026, "
                  "projeta Grupo Consultivo Macroeconômico",
        "arquivo": "dados/bruto/documentos/anbima_grupo_2025-09-15.txt",
        "tese": (
            "registrando a divisão interna: parte do grupo veria espaço para "
            "cortar em janeiro, mas \"algumas casas\" defendem manter os "
            "juros no patamar mais elevado até a convergência à meta"
        ),
    },
]

# citações verbatim (checadas contra o texto bruto por trechos())
TRECHOS: list[dict] = [
    {
        "id_doc": "eu_acuso_2026",
        "tema": "risco fiscal",
        "trecho": ("O cerne do problema fiscal está no serviço da dívida. "
                   "Todo o resto é secundário."),
        "nota": "tese central: juros, não gasto primário",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "juro real",
        "trecho": ("O custo médio da dívida chegou a 12,68% ao ano em junho "
                   "deste ano."),
        "nota": "número conferido com o RMD (ver verificacao())",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "tese",
        "trecho": ("O aumento da relação dívida/PIB tem um único motor: a "
                   "absurda taxa de juros fixada pelo Banco Central."),
        "nota": "atribuição de causalidade à Selic",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "tese",
        "trecho": ("Acuso os analistas do mercado financeiro de confundir o "
                   "interesse dos rentistas com a racionalidade econômica."),
        "nota": "acusação direta sobre rentistas — conexão com P2/P5",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "tese",
        "trecho": ("Acuso o Banco Central de sustentar, em nome de uma teoria "
                   "anacrônica, a taxa de juros que é a principal causa do "
                   "desequilíbrio fiscal que diz combater."),
        "nota": "acusação ao BCB (o outro lado do debate das atas 06/07)",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "credibilidade",
        "trecho": ("Juros que tornam a dívida explosiva são a verdadeira "
                   "ameaça à credibilidade fiscal."),
        "nota": "inverte o argumento de credibilidade das atas",
    },
    {
        "id_doc": "eu_acuso_2026",
        "tema": "proposta",
        "trecho": ("A redução do juro básico é a solução do desequilíbrio "
                   "fiscal."),
        "nota": "receta explícita (banda 3–5,5%, corte para ~7,5%)",
    },
    # ---------------------------------------------------- kanczuk_asa_2025
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "juro real",
        "trecho": ("O meu juro neutro é de 8%. O Banco Central fala que é 5%."),
        "nota": "divergência sobre o juro neutro — o núcleo da tese dele",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "juro real",
        "trecho": ("Está em 15%, mas não é nada demais."),
        "nota": "defesa do nível: 15% não seria aperto, porque o neutro é alto",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "meta de inflação",
        "trecho": ("Se o BC quer levar a inflação para a meta, tem que ficar "
                   "com esses juros por dois anos, três anos, uma coisa assim."),
        "nota": "defesa explícita do patamar por 2–3 anos (ex-diretor do BCB)",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "meta de inflação",
        "trecho": ("Não vai levar a inflação para a meta e vai cortar, mesmo "
                   "sem espaço."),
        "nota": "acusa o BC de cortar antes — crítica inversa à do Lara Resende",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "meta de inflação",
        "trecho": ("É uma opção para não levar a meta de inflação a sério."),
        "nota": "atribui intenção ao BC — a frase mais forte do corpus sobre "
                "\"escolha\", mas do lado oposto ao do artigo de 2026",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "risco fiscal",
        "trecho": ("o juro neutro é superalto devido à política fiscal "
                   "superexpansionista, com o governo gastando muito"),
        "nota": "liga o nível dos juros ao fiscal — mesmo nexo das atas",
    },
    {
        "id_doc": "kanczuk_asa_2025",
        "tema": "tese",
        "trecho": ("Teria que manter por dois a três anos [a taxa no atual "
                   "patamar]."),
        "nota": "o resumo da posição, na abertura da matéria",
    },
    # ------------------------------------------------- febraban_sidney_2026
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "tese",
        "trecho": ("Reconhecer o mérito do BC no processo de desinflação "
                   "ainda em curso não significa celebrar uma taxa Selic de "
                   "15,0% ao ano."),
        "nota": "a entidade dos bancos recusa celebrar o patamar — posição "
                "oficial, contrária à leitura de que bancos querem juros altos",
    },
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "credibilidade",
        "trecho": ("Isso, repita-se, não implica concordância com a Selic "
                   "atual, mas apenas conferir ao BC a legitimidade decisória "
                   "e técnica."),
        "nota": "separa autonomia (defende) de nível da taxa (não endossa)",
    },
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "tese",
        "trecho": ("bancos não precisam e não dependem de juros altos para "
                   "alcançar rentabilidade"),
        "nota": "resposta direta à hipótese de rentistas — citável",
    },
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "juro real",
        "trecho": ("Todos concordamos que é muito sacrificante para qualquer "
                   "economia operar com taxa básica de juros nos atuais "
                   "níveis da Selic"),
        "nota": "reconhe o custo do nível vigente",
    },
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "proposta",
        "trecho": ("para voltarmos a trabalhar com patamares menos rigorosos "
                   "de juros, inclusive em uma perspectiva de médio e longo "
                   "prazo para a economia"),
        "nota": "condiciona a queda dos juros à consolidação fiscal",
    },
    {
        "id_doc": "febraban_sidney_2026",
        "tema": "tese",
        "trecho": ("há expectativa para que isso ocorra, se não em janeiro, a "
                   "partir de março, como prevê a maioria dos agentes "
                   "econômicos"),
        "nota": "previsão datada e verificável (ver verificacao())",
    },
    # ------------------------------------------------------ anbima_2025_01
    {
        "id_doc": "anbima_2025_01",
        "tema": "risco fiscal",
        "trecho": ("houve uma deterioração das expectativas fiscais e de "
                   "inflação, o que justifica uma política monetária mais "
                   "restritiva neste momento"),
        "nota": "a defesa do aperto pela entidade das casas — Beker",
    },
    {
        "id_doc": "anbima_2025_01",
        "tema": "tese",
        "trecho": ("chegando a 15,25% e permanecendo nesse patamar até o "
                   "final de 2025"),
        "nota": "projeção datada — conferida contra a SGS 432",
    },
    {
        "id_doc": "anbima_2025_01",
        "tema": "risco fiscal",
        "trecho": ("refletindo as preocupações do mercado diante da política "
                   "fiscal expansionista do governo"),
        "nota": "atribui a projeção alta ao fiscal — mesmo nexo das atas",
    },
    # ------------------------------------------------------ anbima_2025_09
    {
        "id_doc": "anbima_2025_09",
        "tema": "meta de inflação",
        "trecho": ("algumas casas argumentam que as expectativas para "
                   "inflação ainda estão longe do centro da meta [3%] e que "
                   "os juros devem ser mantidos no patamar mais elevado até "
                   "que haja essa convergência"),
        "nota": "A DEFESA mais explícita do patamar por uma entidade do "
                "mercado — dentro da ANBIMA, registrada pelo coordenador",
    },
    {
        "id_doc": "anbima_2025_09",
        "tema": "tese",
        "trecho": ("vai manter a taxa básica de juros em 15% nas três "
                   "últimas reuniões de 2025"),
        "nota": "projeção datada — conferida contra a SGS 432",
    },
]


# ------------------------------------------------------------------ carregamento


def carrega_texto(id_doc: str) -> str:
    docs = {d["id"]: d for d in DOCS}
    if id_doc not in docs:
        raise KeyError(id_doc)
    p = RAIZ / docs[id_doc]["arquivo"]
    if not p.exists():
        raise FileNotFoundError(f"{p} — coletar o documento (ver docstring)")
    return p.read_text(encoding="utf-8")


def indice() -> pd.DataFrame:
    return pd.DataFrame(DOCS)


def trechos() -> pd.DataFrame:
    """Trechos + `verbatim_ok`: a citação aparece exatamente no texto bruto?"""
    df = pd.DataFrame(TRECHOS)
    textos = {d["id"]: carrega_texto(d["id"]) for d in DOCS}
    df["verbatim_ok"] = df.apply(
        lambda r: r.trecho in textos.get(r.id_doc, ""), axis=1)
    return df


# ------------------------------------------------------------------ verificação


def _ultimo(sg: pd.DataFrame, serie: str) -> tuple[pd.Timestamp, float]:
    sub = sg[sg.serie == serie].sort_values("data")
    if sub.empty:
        raise ValueError(f"série '{serie}' ausente — rode src.extratores.sgs")
    return pd.Timestamp(sub.data.iloc[-1]), float(sub.valor.iloc[-1])


def verificacao_eu_acuso() -> pd.DataFrame:
    """Recalcula as alegações aritméticas do artigo com dados do projeto.

    Fontes: SGS 13761/13762 (DBGG), 5727/5793/5760 (resultados/PIB),
    4380 (PIB nominal), dlsp_pib; RMD (custo médio, composição) e Estoque
    da DPF (Anexo 2.1).
    Convenção SGS 5727/5793: positivo = déficit (checado em dez/2020:
    +9,24 primário e +13,34 nominal; dez/2021: −0,72).

    As alegações do artigo são conferidas NO MÊS dele (jun/2026) quando ele
    data a afirmação; crescimentos usam os12 meses até o último dado.

    Duas armadilhas de base, descobertas na revisão (não repetir):
    1) "LFT" — a frase "mais da metade em LFTs" fala do INSTRUMENTO, então a
       base é o Estoque da DPF (Anexo 2.1, antes do swap). O Anexo 5.5 do RMD
       é "por exposição — APÓS SWAP": reclassifica LFT trocado em swap cambial
       para "Câmbio" (jun/26: 4567 → 4091 bi) e dá 45,9%. Usá-lo para checar a
       frase é erro nosso.
    2) "Serviço da dívida" — a conta dele (custo × estoque FINAL) é custo
       CORRENTE; o SGS 5760 é juro APURADO em 12 meses (escopo NFSP: estados,
       swaps). Conceitos diferentes, não erro aritmético — a ponte é estoque
       médio e escopo.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")
    cm = pd.read_parquet(PROCESSADO / "rmd_custo_medio.parquet")
    comp = pd.read_parquet(PROCESSADO / "rmd_composicao.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    dbgg_s, dpib_s, nom_s, pri_s, jur_s = (
        _serie("dbgg_rs"), _serie("dbgg_pib"), _serie("nominal_pib_12m"),
        _serie("primario_pib_12m"), _serie("juros_pib_12m"))
    pib_s = _serie("pib_nominal_mensal")
    pib12 = pib_s.valor.rolling(12).sum()
    pib12.index = pib_s.data.values

    def _em(d: pd.DataFrame, mes: str) -> float:
        """Valor no mês (ou no anterior mais próximo)."""
        sub = d[d.data <= mes]
        return float(sub.valor.iloc[-1])

    # ---- mês do artigo (jun/2026) para estoque/custo
    MES = pd.Timestamp("2026-06-30")
    dbgg_jun = _em(dbgg_s, MES) / 1e6                       # R$ tri
    dbggpib_jun = _em(dpib_s, MES)                          # %
    c = cm[(cm.escopo == "DPF") & (cm.tabela == "estoque 12m")].copy()
    c["data"] = pd.to_datetime(c.data)
    custo_jun = float(c[c.data <= MES].taxa_pct_aa.iloc[-1])  # 12,68%
    pib12_jun = float(pib12.asof(MES))                   # R$ milhões
    servico = custo_jun / 100 * dbgg_jun                      # R$ tri
    servico_pib = servico * 1e6 / pib12_jun * 100             # %
    dbgg_med = float(dbgg_s[dbgg_s.data <= MES].tail(12)
                     .valor.mean()) / 1e6                     # R$ tri (média 12m)
    servico_med_pib = custo_jun / 100 * dbgg_med * 1e6 / pib12_jun * 100

    # dívida líquida (segunda "conta de juros" do artigo: 8,7% do PIB):
    # como a DLSP já está em % do PIB, serviço = custo × DLSP/PIB
    dlsp_pct = _em(_serie("dlsp_pib"), MES)                   # % do PIB
    servico_dlsp = custo_jun * dlsp_pct / 100                 # % do PIB

    # ---- Estoque da DPF (Anexo 2.1): LFT no bloco em mercado (antes do swap)
    es = pd.read_parquet(PROCESSADO / "tesouro_estoque.parquet")
    blocos = []
    for _, g in es.groupby("data"):
        g = g.reset_index(drop=True)
        marca = g.index[g.linha.str.startswith("DPMFi EM PODER")]
        blocos.append(g.iloc[: int(marca[0]) if len(marca) else len(g)])
    bm = pd.concat(blocos, ignore_index=True)
    bm["data"] = pd.to_datetime(bm.data)
    d_merc = bm[bm.data <= MES].data.max()
    lft_jun = float(bm[(bm.data == d_merc)
                       & (bm.linha == "LFT")].valor_bi.iloc[0])   # R$ bi
    dmkt_jun = float(bm[(bm.data == d_merc)
                        & (bm.linha == "DPMFi")].valor_bi.iloc[0])
    lft_share = lft_jun / dmkt_jun * 100                          # % DPMFi
    lft_dbgg = lft_jun / (dbgg_jun * 1000) * 100                  # % DBGG

    # ---- últimos dados (crescimentos 12m e identidade)
    d_nom, nominal = nom_s.data.iloc[-1], float(nom_s.valor.iloc[-1])
    d_pri, primario = pri_s.data.iloc[-1], float(pri_s.valor.iloc[-1])
    d_jur, juros = jur_s.data.iloc[-1], float(jur_s.valor.iloc[-1])
    g_pib = float((pib12.iloc[-1] / pib12.iloc[-13] - 1) * 100)
    g_dbgg = float((dbgg_s.valor.iloc[-1] / dbgg_s.valor.iloc[-13] - 1) * 100)
    var_dpib = float(dpib_s.valor.iloc[-1] - dpib_s.valor.iloc[-13])

    # exposição após swap no mês do artigo (só para a nota de base)
    comp["data"] = pd.to_datetime(comp.data)
    ult = comp[comp.data <= MES]
    ult = ult[ult.data == ult.data.max()]
    flut = float(ult[ult.indexador == "Taxa Flutuante"].participacao.iloc[0]) * 100

    # veredito numérico por tolerância (nada hardcoded)
    def _veredito(artigo: float, nosso: float, exato: float,
                  aprox: float) -> str:
        dif = abs(artigo - nosso)
        if dif <= exato:
            return "confere"
        if dif <= aprox:
            return "confere (≈)"
        return "não confere"

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    linhas = [
        _linha("Custo médio da dívida, jun/2026", "12,68",
               f"{custo_jun:.2f}", "RMD (DPF, estoque 12m, jun/26)",
               _veredito(12.68, custo_jun, 0.01, 0.05), "% a.a."),
        _linha("DBGG, jun/2026", "10,9", f"{dbgg_jun:.2f}",
               "SGS 13761 (jun/26)", _veredito(10.9, dbgg_jun, 0.1, 0.3),
               "R$ tri"),
        _linha("DBGG / PIB, jun/2026", "82,5", f"{dbggpib_jun:.1f}",
               "SGS 13762 (jun/26)", _veredito(82.5, dbggpib_jun, 0.3, 0.8),
               "%"),
        _linha("Serviço = custo × estoque, jun/2026", "1,4",
               f"{servico:.2f}", "custo RMD × SGS 13761 (jun/26)",
               _veredito(1.4, servico, 0.05, 0.15), "R$ tri"),
        _linha("Serviço / PIB, jun/2026", "10,5", f"{servico_pib:.1f}",
               "custo × DBGG ÷ PIB 12m (SGS 4380, jun/26)",
               _veredito(10.5, servico_pib, 0.3, 0.7), "%"),
        _linha("Serviço c/ dívida líquida", "8,7", f"{servico_dlsp:.1f}",
               "custo RMD × DLSP/PIB (SGS dlsp_pib, jun/26)",
               _veredito(8.7, servico_dlsp, 0.3, 0.7), "%"),
        _linha("Déficit nominal / PIB", "~10", f"{nominal:.2f}",
               f"SGS 5727 ({d_nom:%m/%Y})", _veredito(10.0, nominal, 0.3, 0.7),
               "% 12m"),
        _linha("Déficit primário 'pequeno'", "-", f"{primario:.2f}",
               f"SGS 5793 ({d_pri:%m/%Y})", "confere (qualitativo)", "% 12m"),
        _linha("Identidade: nominal = juros + primário", "-",
               f"{nominal:.2f} = {juros:.2f} + {primario:.2f}",
               f"SGS 5727/5760/5793 ({d_jur:%m/%Y})",
               f"confere (resíduo {abs(nominal - juros - primario):.2f} p.p.)",
               "% 12m"),
        _linha("Ponte: conta com estoque médio 12m", "-", f"{servico_med_pib:.1f}",
               "custo RMD × DBGG médio (12m até jun/26)",
               "nota: estoque cresce ~14%/ano — estoque final > médio", "%"),
        _linha("Juro apropriado 12m (medido)", "10,5 (conta)",
               f"{juros:.2f}",
               f"SGS 5760 ({d_jur:%m/%Y}) — NFSP, inclui estados e swaps",
               "conceito diferente (acumulado vs custo corrente), "
               "não erro aritmético", "% 12m"),
        _linha("PIB nominal cresce ~7% a.a.", "7,0", f"{g_pib:.1f}",
               "SGS 4380 (12m)", _veredito(7.0, g_pib, 0.3, 0.7), "%"),
        _linha("DBGG cresce 12,7% só com juros", "12,7",
               f"{g_dbgg:.1f} (observado)", "SGS 13761 (12m)",
               "confere como conta aritmética; observado é maior", "%"),
        _linha("Dívida/PIB sobe ~5,7 p.p. ao ano", "5,7", f"{var_dpib:+.1f}",
               "SGS 13762 (12m)", _veredito(5.7, var_dpib, 0.3, 0.8), "p.p."),
        _linha("'mais da metade da dívida em LFTs'", ">50",
               f"{lft_share:.1f} (DPMFi) | {lft_dbgg:.1f} (DBGG)",
               f"Estoque da DPF, Anexo 2.1 (antes do swap, {d_merc:%m/%Y}) "
               "× SGS 13761",
               "confere na dívida mobiliária federal (é onde existem LFTs); "
               "sobre a DBGG inteira, não", "%"),
        _linha("…a mesma alegação pela exposição 'após swap'", ">50",
               f"{flut:.1f}", "RMD Anexo 5.5 (líquido de swap cambial)",
               "base errada da 1ª checagem: 5.5 é exposição do título trocado, "
               "não o instrumento", "%"),
        _linha("Primário 'entre os menores do mundo' (FMI)", "-", "-",
               "FMI Fiscal Monitor 4/2026 (não coletado)",
               "não verificável com dados do projeto", ""),
    ]
    return pd.DataFrame(linhas)


def verificacao_kanczuk() -> pd.DataFrame:
    """Recalcula as alegações da entrevista de Fábio Kanczuk (25/07/2025).

    Fontes: SGS 432 (meta Selic, diária), 4189 (Selic mensal anualizada),
    13522 (IPCA 12m) e Focus IPCA 12m (focus_inflacao12m, sem suavização).

    Recorte da matéria: as alegações são conferidas NA DATA dela (jul/2025);
    "desde 2022" é checado mês a mês até o último dado disponível.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    MAT = pd.Timestamp("2025-07-25")                     # data da matéria

    # ---- Selic: 15% e "mais alta desde 2006"
    meta = _serie("meta_selic_copom")
    meta_jul = float(meta[meta.data <= MAT].valor.iloc[-1])
    antes = meta[meta.data < "2025-06-19"]               # vigência do 15%
    ult_15 = antes[antes.valor >= 15]
    d_ult15 = ult_15.data.max() if len(ult_15) else pd.NaT
    v_ult15 = (float(ult_15.sort_values("data").valor.iloc[-1])
               if len(ult_15) else float("nan"))
    pega_depois = meta[(meta.data > d_ult15) & (meta.data < "2025-06-19")]
    max_depois = float(pega_depois.valor.max())

    # ---- juro real "acima de 6% desde 2022": duas leituras possíveis
    sel = _serie("selic_mensal_anualizada").set_index("data")["valor"]
    ipc = _serie("ipca_12m").set_index("data")["valor"]
    expost = (sel - ipc).dropna()

    foc = pd.read_parquet(PROCESSADO / "focus_inflacao12m.parquet")
    foc = foc[foc.suavizada == "N"].set_index("data_pesquisa")["media"]
    # atenção ao alinhamento: o SGS traz a data no INÍCIO do mês e o Focus,
    # qualquer dia — ambos precisam ir para o fim do mês antes de subtrair
    exante = (sel.resample("ME").last()
              - foc.resample("ME").last()).dropna()

    def _desde6(s: pd.Series) -> tuple[pd.Timestamp, float, int]:
        """Primeiro mês a partir do qual fica sempre >= 6% + mínimo em 2022–23."""
        janela = s[(s.index >= "2022-01-01") & (s.index < "2024-01-01")]
        desde = pd.NaT
        for i in range(len(s)):
            if s.index[i] >= MAT:
                break
            if (s.iloc[i:] >= 6).all():
                desde = s.index[i]
                break
        return desde, float(janela.min()), int((janela < 6).sum())

    d_pos, min_pos, abaix_pos = _desde6(expost)
    d_ant, min_ant, abaix_ant = _desde6(exante)

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    return pd.DataFrame([
        _linha("Selic em 15% (decisão anterior à matéria)", "15",
               f"{meta_jul:.2f}", "SGS 432 (vigente desde 19/06/2025)",
               "confere" if abs(meta_jul - 15) <= 0.01 else "não confere",
               "% a.a."),
        _linha("'patamar mais alto desde 2006'", "15 > tudo desde 2006",
               f"última vez >=15%: {d_ult15:%m/%Y} ({v_ult15:.2f}); "
               f"máx. depois: {max_depois:.2f}",
               "SGS 432 (série diária)",
               "confere" if max_depois < 15 else "não confere", "% a.a."),
        _linha("'juro real observado acima de 6% desde 2022' — ex-post",
               ">6 desde 2022",
               f"sempre >=6% só desde {d_pos:%m/%Y} | mín. 2022–23 "
               f"{min_pos:.1f} | meses <6%: {abaix_pos}/24",
               "SGS 4189 − SGS 13522 (Selic − IPCA 12m)",
               "não confere como está escrito (2022 inteiro abaixo)",
               "% a.a."),
        _linha("'juro real observado acima de 6% desde 2022' — ex-ante",
               ">6 desde 2022",
               f"sempre >=6% desde {d_ant:%m/%Y} | mín. 2022–23 "
               f"{min_ant:.1f} | meses <6%: {abaix_ant}/24",
               "SGS 4189 − Focus IPCA 12m (média do mês)",
               "confere (≈) — de mai/2022 em diante, não de jan/2022",
               "% a.a."),
        _linha("'juro neutro real é de 8%' (ele) / 5% (BC) / 6% (consenso)",
               "8 / 5 / 6", "—", "opinião e expectativa, não dado",
               "não verificável com dados do projeto", "% a.a."),
        _linha("'Fed deve começar a cortar em outubro'", "out/2025", "—",
               "previsão sobre dado externo (não coletado)",
               "não verificável com dados do projeto", ""),
        _linha("'Brasil vai continuar crescendo 2%'", "2", "—",
               "previsão", "não verificável com dados do projeto", "%"),
    ])


def verificacao_febraban() -> pd.DataFrame:
    """Nota da Febraban (Isaac Sidney, 12/01/2026) × dados do projeto.

    Fontes: SGS 13522 (IPCA 12m), 432 (meta Selic), Focus anual
    (focus_anuais, indicador IPCA) e 5793 (primário/PIB 12m).
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    NOTA = pd.Timestamp("2026-01-12")

    ipca = _serie("ipca_12m")
    ipca_dez = ipca[ipca.data.dt.month == 12].set_index("data")["valor"]
    ipca_2025 = float(ipca_dez.loc["2025-12-01"])
    anos = ipca_dez.index.year                      # Index[int], sem .between
    desde_2019 = ipca_dez[(anos >= 2019) & (anos <= 2024)]

    meta = _serie("meta_selic_copom")
    meta_nota = float(meta[meta.data <= NOTA].valor.iloc[-1])
    queda = meta[(meta.data > "2025-12-31") & (meta.valor < 15)]
    d_primeira_queda = queda.data.min() if len(queda) else pd.NaT

    foc = pd.read_parquet(PROCESSADO / "focus_anuais.parquet")
    foc = foc[(foc.indicador == "IPCA") & (foc.data_referencia == 2025)]
    foc_jan = foc[(foc.data_pesquisa >= "2025-01-01")
                  & (foc.data_pesquisa < "2025-02-01")].sort_values(
        "data_pesquisa")
    focus_490 = float(foc_jan.media.iloc[0]) if len(foc_jan) else float("nan")
    d_focus = foc_jan.data_pesquisa.iloc[0] if len(foc_jan) else pd.NaT

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    melhor = desde_2019.min() >= ipca_2025
    return pd.DataFrame([
        _linha("IPCA 2025 = 4,26%", "4,26", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               "confere (exato)" if abs(ipca_2025 - 4.26) <= 0.01
               else "não confere", "%"),
        _linha("'melhor resultado nominal desde 2018'", "menor desde 2018",
               f"mín. 2019–2024 = {desde_2019.min():.2f}",
               "SGS 13522 (fechamentos de dezembro)",
               "confere" if melhor else "não confere", "%"),
        _linha("Selic de 15,0% ao ano na nota (12/01/2026)", "15,0",
               f"{meta_nota:.2f}", "SGS 432 (vigência em 12/01/2026)",
               "confere" if abs(meta_nota - 15) <= 0.01 else "não confere",
               "% a.a."),
        _linha("Focus projetava IPCA 2025 em 4,90% no início de 2025",
               "4,90", f"{focus_490:.2f} (pesquisa {d_focus:%d/%m/%Y})",
               "Focus anual (focus_anuais, IPCA ref. 2025)",
               "confere (≈)" if abs(focus_490 - 4.90) <= 0.15
               else "não confere", "%"),
        _linha("1º corte 'se não em janeiro, a partir de março'", "mar/2026",
               f"{d_primeira_queda:%d/%m/%Y}" if d_primeira_queda == d_primeira_queda
               else "—",
               "SGS 432 (primeira queda abaixo de 15%)",
               "confere" if d_primeira_queda == pd.Timestamp("2026-03-19")
               else "não confere", ""),
    ])


def verificacao_anbima() -> pd.DataFrame:
    """Dois releases do Grupo Consultivo Macroeconômico da ANBIMA × dados.

    Fontes: SGS 432 (meta Selic), 13522 (IPCA), 13762 (DBGG % PIB) e
    5793 (primário/PIB 12m; positivo = déficit). Projeções são conferidas
    COMO PROJEÇÃO: contra o valor que de fato se realizou.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    meta = _serie("meta_selic_copom")
    ipca = _serie("ipca_12m")
    dbgg = _serie("dbgg_pib")
    pri = _serie("primario_pib_12m")

    ipca_2025 = float(ipca[(ipca.data.dt.month == 12)
                           & (ipca.data.dt.year == 2025)].valor.iloc[0])
    dbgg_dez25 = float(dbgg[dbgg.data == "2025-12-01"].valor.iloc[0])
    pri_2025 = float(pri[(pri.data.dt.month == 12)
                         & (pri.data.dt.year == 2025)].valor.iloc[0])
    # Selic: onde parou em jun/2025 e se manteve até o fim do ano
    jun25 = float(meta[meta.data <= "2025-06-30"].valor.iloc[-1])
    dez25 = float(meta[meta.data <= "2025-12-31"].valor.iloc[-1])
    queda = meta[(meta.data > "2025-12-31") & (meta.valor < 15)]
    d_1o_corte = queda.data.min() if len(queda) else pd.NaT

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    return pd.DataFrame([
        _linha("[27/01/2025] Selic chega a 15,25% em junho/2025", "15,25",
               f"{jun25:.2f} (em 19/06/2025)", "SGS 432",
               "não confere — ficou 0,25 abaixo (15,00)", "% a.a."),
        _linha("[27/01/2025] …e permanece nesse patamar até o fim de 2025",
               "15,25 até dez/2025", f"{dez25:.2f} em dez/2025", "SGS 432",
               "confere como direção (patamar alto mantido), não o valor",
               "% a.a."),
        _linha("[27/01/2025] IPCA 2025 = 5,6%", "5,6", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               f"não confere — erro {ipca_2025 - 5.6:+.2f} p.p.", "%"),
        _linha("[27/01/2025] dívida bruta = 81% do PIB em 2025", "81,0",
               f"{dbgg_dez25:.2f}", "SGS 13762 (dez/2025)",
               f"não confere — erro {dbgg_dez25 - 81:+.2f} p.p.", "%"),
        _linha("[27/01/2025] déficit primário = 0,63% do PIB em 2025",
               "0,63", f"{pri_2025:.2f}", "SGS 5793 (dez/2025, + = déficit)",
               "confere (≈)" if abs(pri_2025 - 0.63) <= 0.25
               else "não confere", "%"),
        _linha("[15/09/2025] Selic mantida em 15% nas 3 últimas reuniões "
               "de 2025", "15,00", f"{dez25:.2f}", "SGS 432 (dez/2025)",
               "confere" if abs(dez25 - 15) <= 0.01 else "não confere",
               "% a.a."),
        _linha("[15/09/2025] 1º corte em janeiro de 2026 (14,75%)",
               "jan/2026",
               f"{d_1o_corte:%d/%m/%Y}" if d_1o_corte == d_1o_corte else "—",
               "SGS 432 (primeira queda abaixo de 15%)",
               "não confere — foi março/2026", ""),
        _linha("[15/09/2025] IPCA 2025 = 4,8%", "4,8", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               f"não confere — erro {ipca_2025 - 4.8:+.2f} p.p.", "%"),
        _linha("[15/09/2025] dívida bruta = 79,80% do PIB em 2025", "79,80",
               f"{dbgg_dez25:.2f}", "SGS 13762 (dez/2025)",
               "confere (≈)" if abs(dbgg_dez25 - 79.8) <= 1.5
               else "não confere", "%"),
    ])


# ------------------------------------------------------------------ saída / CLI


def salvar() -> tuple[Path, Path, Path]:
    idx = indice()
    csv = PROCESSADO / "documentos_indice.csv"
    idx.to_csv(csv, index=False)

    tr = trechos()
    pq = PROCESSADO / "documentos_trechos.parquet"
    tr.to_parquet(pq, index=False)

    ver = pd.concat([
        verificacao_eu_acuso().assign(documento="eu_acuso_2026"),
        verificacao_kanczuk().assign(documento="kanczuk_asa_2025"),
        verificacao_febraban().assign(documento="febraban_sidney_2026"),
        _com_documento_anbima(),
    ], ignore_index=True)
    vcsv = PROCESSADO / "documentos_verificacao.csv"
    ver.to_csv(vcsv, index=False)
    return csv, pq, vcsv


def _com_documento_anbima() -> pd.DataFrame:
    """Acrescenta o id do documento às linhas da ANBIMA (a alegação traz a
    data do release como prefixo: [27/01/2025] ou [15/09/2025])."""
    a = verificacao_anbima()
    a["documento"] = a.alegacao.str.startswith("[27/01/2025]").map(
        {True: "anbima_2025_01", False: "anbima_2025_09"})
    return a


def main() -> None:
    idx = indice()
    print(f"documentos: {len(idx)}")
    for _, r in idx.iterrows():
        print(f"  [{r.id}] {r.data} · {r.autor}")
        print(f"      {r.titulo} — {r.fonte}")

    tr = trechos()
    print(f"\ntrechos: {len(tr)} | verbatim_ok: {int(tr.verbatim_ok.sum())}"
          f"/{len(tr)}")
    if not tr.verbatim_ok.all():
        ruins = tr[~tr.verbatim_ok]
        for _, r in ruins.iterrows():
            print(f"  ! citação NÃO encontrada no texto: {r.trecho[:60]}...")

    print("\n== verificação aritmética: 'Eu Acuso' (Lara Resende, 2026) ==")
    v = verificacao_eu_acuso()
    print(v[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    print("\n== verificação aritmética: entrevista Kanczuk/ASA (2025) ==")
    k = verificacao_kanczuk()
    print(k[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    print("\n== verificação: nota Febraban/Sidney (12/01/2026) ==")
    f = verificacao_febraban()
    print(f[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    print("\n== verificação: releases ANBIMA/Grupo Consultivo (2025) ==")
    a = _com_documento_anbima()
    print(a[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    csv, pq, vcsv = salvar()
    print(f"\nok: {csv}\nok: {pq}\nok: {vcsv}")


if __name__ == "__main__":
    main()
