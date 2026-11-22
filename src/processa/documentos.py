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

`verificacao_eu_acuso()`, `verificacao_kanczuk()`, `verificacao_febraban()`,
`verificacao_anbima()`, `verificacao_bresser()` e `verificacao_lara_nota()`
recalculam a aritmética de cada documento com as séries do projeto
(SGS/Focus/RMD) — nada é aceito sem conferência. É um padrão repetível: para
cada novo documento de posição, uma função de verificação.

Saídas:
- dados/processado/documentos_indice.csv
- dados/processado/documentos_trechos.parquet
- dados/processado/documentos_verificacao.csv (uma linha por alegação;
  `documento` identifica a fonte)

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
    {
        "id": "bresser_lara_resende_2026",
        "tipo": "artigo de opinião (endosso)",
        "autor": ("Luiz Carlos Bresser-Pereira (ex-ministro da Fazenda; "
                  "professor emérito da FGV-SP)"),
        "data": "2026-11-04",
        "fonte": "Substack — Luiz Carlos Bresser Pereira",
        "url": ("https://luizcarlosbresserpereira885213.substack.com/p/"
                "a-proposta-de-andre-lara-resende"),
        "titulo": "A proposta de Lara Resende para baixar os juros",
        "arquivo": "dados/bruto/documentos/bresser_lara_resende_2026-11-04.txt",
        "tese": (
            "endossa a proposta de Lara Resende: Selic gradual para 7,5% a.a. "
            "em 12 meses (meta de 3% + 2,5% de crescimento + 2% de spread), "
            "com ajuste fiscal de ~4% do PIB sobre rentistas; repete a "
            "equação 4,5% = 7,5% − 3% + 2% (que dá 6,5%) e o dado de 40% dos "
            "títulos negociados na Bolsa com estrangeiros — compatível com "
            "o NTN-F (40,2% em set/26), não com o estoque total"
        ),
    },
    {
        "id": "lara_nota_2026_11",
        "tipo": "artigo de posição (continuação)",
        "autor": "André Lara Resende (ex-presidente do BCB)",
        "data": "2026-11-16",
        "fonte": "Substack — Um Cético Esperançoso",
        "url": ("https://andrelararesende.substack.com/p/"
                "uma-nota-sobre-a-proposta-de-meta"),
        "titulo": "Uma nota sobre a proposta de meta para os juros",
        "arquivo": ("dados/bruto/documentos/"
                    "uma_nota_meta_juros_lara_resende_2026-11-16.txt"),
        "tese": (
            "responde às objeções à proposta de set/2026: a meta para a Selic "
            "vira um intervalo entre a inflação (piso) e o crescimento nominal "
            "da renda (teto), a ser atingido em 2–4 anos, com forward guidance "
            "e coordenação fiscal-monetária; fora do intervalo só em condições "
            "extraordinárias justificadas em carta aberta. Defende que o BC "
            "pauta a curva (correlações de 0,95 e 0,85) e que o juro alto "
            "encarece o financiamento das empresas e das famílias"
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
    # ------------------------------------------------ bresser_lara_resende_2026
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "tese",
        "trecho": ("É uma excelente proposta que, se adotada pelo governo, "
                   "deverá ser amplamente discutida pelos seus representantes "
                   "principais no Minimstério da Fazenda e no Banco Central"),
        "nota": "endosso explícito — é posição, não medição (typo do original)",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "juro real",
        "trecho": ("Uma taxa de juros desse nível inviabiliza grande parte "
                   "dos investimentos"),
        "nota": "custo do nível sobre o investimento",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "tese",
        "trecho": ("representa uma grande transferência de renda da população "
                   "em geral para rentistas e financistas"),
        "nota": "a hipótese distributiva (P2) dita sem meias palavras",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "risco fiscal",
        "trecho": ("A alta dos juros não reduz a inflação; ao contrário, se "
                   "não houver uma contração fiscal simultânea, irá elevar a "
                   "inflação."),
        "nota": "argumento neofisheriano atribuído a Cochrane — posição teórica",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "proposta",
        "trecho": ("O BC se comprometeria a manter a taxa básica se "
                   "aproximando gradualmente para 7,5%, a.a., em doze meses."),
        "nota": "a proposta em uma frase — meta de 12 meses",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "proposta",
        "trecho": ("Teríamos, então, 3,0% de meta de inflação, mais 2,5 de "
                   "crescimento do PIB, mais 2% de spread transitório de "
                   "segurança."),
        "nota": "decomposição que soma 7,5%, mas 2,5% é PIB, não juro neutro",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "proposta",
        "trecho": ("um ajuste fiscal de cerca de 4% do PIB, que afetaria "
                   "apenas os rentistas e financistas"),
        "nota": "magnitude e incidência do ajuste — conferida em 4,25% (≈)",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "tese",
        "trecho": "capturam há muitos anos 5% do PIB",
        "nota": "estimativa de Bresser — não é o fluxo total medido (6,91%)",
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "risco externo",
        "trecho": ("Como cerca de 40% dos títulos do governo negociados na "
                   "Bolsa de valores pertencem a estrângeiros"),
        "nota": ("compatível com o NTN-F (40,2% em set/26); a base "
                 "'negociados na Bolsa' não está especificada; o "
                 "estoque total é 10,0% — bases diferentes; typo do "
                 "original"),
    },
    {
        "id_doc": "bresser_lara_resende_2026",
        "tema": "proposta",
        "trecho": ("o governo deverá tranquilizar os mercados através da "
                   "verda de reservas"),
        "nota": "proposta sem série no catálogo — não testável (typo do original)",
    },
    # ------------------------------------------------- lara_nota_2026_11
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "tese",
        "trecho": "Reduzir os juros é a única saída.",
        "nota": "a tese em uma frase; continua a proposta de set/2026",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "proposta",
        "trecho": ("O Banco Central anunciaria uma meta para a taxa Selic, "
                   "definida pelo intervalo entre a inflação, o piso, e o "
                   "crescimento nominal da renda, o teto do intervalo."),
        "nota": ("mudança de destino e horizonte: de um ponto (~7,5%) "
                 "para um intervalo; a trajetória gradual já estava "
                 "no texto de set/2026"),
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "proposta",
        "trecho": ("O piso evita os juros reais negativos da repressão "
                   "financeira; o teto garante que a relação dívida/PIB se "
                   "estabilize."),
        "nota": "racional do intervalo: piso contra repressão financeira, "
                "teto contra explosão da dívida",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "proposta",
        "trecho": ("Só em condições extraordinárias, justificadas em carta "
                   "aberta, a taxa básica ficaria fora desse intervalo."),
        "nota": "cláusula de exceção — não é tabelamento nem regra rígida",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "proposta",
        "trecho": ("proponho que o prazo para atingir o intervalo meta seja "
                   "algo entre dois e quatro anos"),
        "nota": "prazo novo em relação ao texto de set/2026 (12 meses)",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "proposta",
        "trecho": ("É uma política de “forward guidance”, como já fazem os "
                   "bancos centrais desde o início deste século, com a "
                   "novidade de explicitar a coordenação das políticas "
                   "fiscal e monetária."),
        "nota": "enquadra a proposta como forward guidance + coordenação "
                "fiscal-monetária",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "juro real",
        "trecho": ("Os dados do próprio Tesouro Nacional, no Relatório "
                   "Mensal da Dívida, mostram que, entre 2011 e 2022, o custo "
                   "médio das novas emissões e do estoque da dívida pública "
                   "acompanhou de perto a trajetória da Selic."),
        "nota": "resposta à objeção de que o BC controla só a taxa de um dia",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "juro real",
        "trecho": ("Correlação não significa causalidade, mas neste caso não "
                   "há dúvida sobre a direção: a Selic é o instrumento do BC, "
                   "e o custo médio da dívida, que reflete as taxas para os "
                   "diferentes prazos dos títulos, é a consequência."),
        "nota": "a direção causal que ele afirma — é o ponto teórico, não o "
                "coeficiente",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "juro real",
        "trecho": ("Entre dezembro de 2011 e setembro de 2026, o custo médio "
                   "das emissões em oferta pública da dívida interna, "
                   "acumulado em 12 meses, teve correlação de 0,95 com a "
                   "Selic acumulada no mesmo período."),
        "nota": "número novo; o RMD 4.3 só começa em 01/2021 (nova "
                "metodologia) — proxy do estoque: 0,84, não 0,95",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "juro real",
        "trecho": ("Entre janeiro de 2011 e outubro de 2026, a taxa do título "
                   "prefixado de dez anos do Tesouro acompanhou a trajetória "
                   "da Selic, com correlação de 0,85 entre as taxas mensais."),
        "nota": "número novo; sem série de 10 anos no catálogo — proxy de "
                "emissões NTN-F 2021–26 dá 0,93",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "juro real",
        "trecho": ("No ciclo de alta iniciado em 2021, que levou a Selic de "
                   "1,9% para 14,9% ao ano, a taxa de dez anos subiu de 7,5% "
                   "para perto de 15%."),
        "nota": "Selic confere na série efetiva; a taxa de 10 anos não está "
                "no catálogo — proxy de emissões NTN-F: 7,2% (2021) → 14,3% "
                "(2025)",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "mercado financeiro",
        "trecho": ("Não é “a curva” que pauta o BC, mas o BC quem pauta, ou "
                   "deveria pautar, o mercado."),
        "nota": "a tese institucional: o BC determina a estrutura a termo, "
                "não o contrário",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "tese",
        "trecho": ("Em 2025, a companhia brasileira típica investiu o "
                   "equivalente a 91% da sua depreciação, menos do que o "
                   "necessário para repor o capital que se desgasta."),
        "nota": "custo do juro sobre o investimento — sem série de "
                "investimento/depreciação no catálogo",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "tese",
        "trecho": ("Em 2025, a Serasa Experian registrou 977 pedidos de "
                   "recuperação judicial, o maior número desde 2016 e mais de "
                   "50% acima da média histórica, de 53 pedidos por mês."),
        "nota": "evidência de estresse das empresas — sem série Serasa no "
                "catálogo",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "tese",
        "trecho": ("Em agosto de 2026, suas dívidas com o sistema financeiro "
                   "chegaram a 50,1% da renda acumulada em doze meses, e o "
                   "pagamento dessas dívidas consumia cerca de 29% da renda "
                   "mensal, ambos recordes nas séries do Banco Central."),
        "nota": "endividamento das famílias — sem série no catálogo",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "risco fiscal",
        "trecho": ("o custo da dívida, devido à insistência equivocada do "
                   "Banco Central em fixar a Selic em níveis extraordinariamente "
                   "altos, é o principal fator por trás do déficit público e "
                   "do crescimento da dívida."),
        "nota": "a causalidade central, repetida na conclusão",
    },
    {
        "id_doc": "lara_nota_2026_11",
        "tema": "câmbio",
        "trecho": ("Praticamente não temos dívida pública externa. Temos "
                   "reservas cambiais expressivas. Além disso, os dólares de "
                   "exportadores mantidos no exterior, que poderiam ser "
                   "internalizados por simples revisão das normas do Conselho "
                   "Monetário Nacional, elevam esse colchão para mais de "
                   "US$ 400 bilhões."),
        "nota": "resposta ao risco cambial — sem série de reservas "
                "internacionais no catálogo",
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


# --------------------------------------------- parâmetros de referência
# Datas de recorte e limiares das checagens aritméticas (as alegações em
# si — o que cada documento diz — ficam em verificacao_* como texto
# citado). Fonte de cada valor na função correspondente; nada de literal
# inline: mudar aqui muda a checagem.

# "Eu Acuso" (Lara Resende, artigo de jun/2026)
MES_ARTIGO = pd.Timestamp("2026-06-30")        # mês do artigo

# Entrevista Kanczuk/ASA (25/07/2025)
MAT_KANCZUK = pd.Timestamp("2025-07-25")       # data da matéria
JURO_REAL_DE = "2022-01-01"                    # alegação: "desde 2022"
JURO_REAL_ATE = "2024-01-01"                   # janela 2022–23 (mín./meses <)
LIMIAR_JURO_REAL = 6                           # alegação: "acima de 6%"

# patamar de Selic citado por Kanczuk, Febraban e ANBIMA ("15%")
SELIC_PATAMAR = 15

# Nota Febraban/Sidney (12/01/2026)
NOTA_FEBRABAN = pd.Timestamp("2026-01-12")     # data da nota
IPCA_MELHOR_DESDE = 2018                       # alegação: "melhor desde 2018"


# ------------------------------------------------------------------ verificação


def _veredito(artigo: float, nosso: float) -> str:
    """Veredito numérico por tolerância RELATIVA — régua única, definida a
    priori e aplicada a todas as verificações: erro relativo ≤ 2% confere,
    ≤ 10% confere (≈), acima disso não confere.

    (Tolerâncias absolutas por caso eram escolhidas à mão e ficavam
    incoerentes entre si: o déficit primário da ANBIMA, com erro de 32%,
    "conferia", enquanto o IPCA da mesma nota, com erro de 24%, não.)
    """
    rel = abs(artigo - nosso) / max(abs(artigo), 0.01)
    if rel <= 0.02:
        return "confere"
    if rel <= 0.10:
        return "confere (≈)"
    return "não confere"


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
    MES = MES_ARTIGO                            # mês do artigo (centralizado)
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

    # veredito numérico: _veredito (régua relativa única do módulo)

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    linhas = [
        _linha("Custo médio da dívida, jun/2026", "12,68",
               f"{custo_jun:.2f}", "RMD (DPF, estoque 12m, jun/26)",
               _veredito(12.68, custo_jun), "% a.a."),
        _linha("DBGG, jun/2026", "10,9", f"{dbgg_jun:.2f}",
               "SGS 13761 (jun/26)", _veredito(10.9, dbgg_jun),
               "R$ tri"),
        _linha("DBGG / PIB, jun/2026", "82,5", f"{dbggpib_jun:.1f}",
               "SGS 13762 (jun/26)", _veredito(82.5, dbggpib_jun),
               "%"),
        _linha("Serviço = custo × estoque, jun/2026", "1,4",
               f"{servico:.2f}", "custo RMD × SGS 13761 (jun/26)",
               _veredito(1.4, servico), "R$ tri"),
        _linha("Serviço / PIB, jun/2026", "10,5", f"{servico_pib:.1f}",
               "custo × DBGG ÷ PIB 12m (SGS 4380, jun/26)",
               _veredito(10.5, servico_pib), "%"),
        _linha("Serviço c/ dívida líquida", "8,7", f"{servico_dlsp:.1f}",
               "custo RMD × DLSP/PIB (SGS dlsp_pib, jun/26)",
               _veredito(8.7, servico_dlsp), "%"),
        _linha("Déficit nominal / PIB", "~10", f"{nominal:.2f}",
               f"SGS 5727 ({d_nom:%m/%Y})", _veredito(10.0, nominal),
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
               "SGS 4380 (12m)", _veredito(7.0, g_pib), "%"),
        _linha("DBGG cresce 12,7% só com juros", "12,7",
               f"{g_dbgg:.1f} (observado)", "SGS 13761 (12m)",
               "confere como conta aritmética; observado é maior", "%"),
        _linha("Dívida/PIB sobe ~5,7 p.p. ao ano", "5,7", f"{var_dpib:+.1f}",
               "SGS 13762 (12m)", _veredito(5.7, var_dpib), "p.p."),
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
    "desde 2022" é checado mês a mês ATÉ A DATA DA MATÉRIA (25/07/2025) —
    dado posterior não reescreve a checagem histórica.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    MAT = MAT_KANCZUK                     # data da matéria (centralizado)

    # ---- Selic: 15% e "mais alta desde 2006"
    meta = _serie("meta_selic_copom")
    meta_jul = float(meta[meta.data <= MAT].valor.iloc[-1])
    antes = meta[meta.data < "2025-06-19"]               # vigência do 15%
    ult_15 = antes[antes.valor >= SELIC_PATAMAR]
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
    # base 0 = base padrão; a base 1 coexiste desde 2014 (ver extrator).
    foc = foc[(foc.suavizada == "N") & (foc.base_calculo == 0)]
    foc = foc.set_index("data_pesquisa")["media"]
    # atenção ao alinhamento: o SGS traz a data no INÍCIO do mês e o Focus,
    # qualquer dia — ambos precisam ir para o fim do mês antes de subtrair
    exante = (sel.resample("ME").last()
              - foc.resample("ME").last()).dropna()

    def _desde6(s: pd.Series) -> tuple[pd.Timestamp, float, int]:
        """Primeiro mês < MAT a partir do qual fica sempre >= 6% ATÉ A
        MATÉRIA + mínimo em 2022–23."""
        # Recorte da matéria (25/07/2025): dado posterior não pode
        # reescrever a checagem histórica (senão um dado novo <6% no
        # futuro apagaria o "desde" já apurado).
        s = s[s.index < MAT]
        janela = s[(s.index >= JURO_REAL_DE) & (s.index < JURO_REAL_ATE)]
        desde = pd.NaT
        for i in range(len(s)):
            if (s.iloc[i:] >= LIMIAR_JURO_REAL).all():
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
               _veredito(SELIC_PATAMAR, meta_jul),
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

    NOTA = NOTA_FEBRABAN                        # data da nota (centralizado)

    ipca = _serie("ipca_12m")
    ipca_dez = ipca[ipca.data.dt.month == 12].set_index("data")["valor"]
    ipca_2025 = float(ipca_dez.loc["2025-12-01"])
    anos = ipca_dez.index.year                      # Index[int], sem .between
    # "melhor resultado desde 2018": lido como os anos POSTERIORES a 2018
    # (2019–2024). Incluindo 2018 (IPCA 3,75%), o mínimo da janela seria
    # menor que o de 2025 e a frase não se sustentaria — a ambiguidade do
    # "desde" fica declarada no status.
    desde_2018 = ipca_dez[(anos > IPCA_MELHOR_DESDE) & (anos <= 2024)]

    meta = _serie("meta_selic_copom")
    meta_nota = float(meta[meta.data <= NOTA].valor.iloc[-1])
    queda = meta[(meta.data > "2025-12-31") & (meta.valor < SELIC_PATAMAR)]
    d_primeira_queda = queda.data.min() if len(queda) else pd.NaT

    foc = pd.read_parquet(PROCESSADO / "focus_anuais.parquet")
    foc = foc[(foc.indicador == "IPCA") & (foc.data_referencia == 2025)
              & (foc.base_calculo == 0)]
    foc_jan = foc[(foc.data_pesquisa >= "2025-01-01")
                  & (foc.data_pesquisa < "2025-02-01")].sort_values(
        "data_pesquisa")
    focus_490 = float(foc_jan.media.iloc[0]) if len(foc_jan) else float("nan")
    d_focus = foc_jan.data_pesquisa.iloc[0] if len(foc_jan) else pd.NaT

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    melhor = desde_2018.min() >= ipca_2025
    return pd.DataFrame([
        _linha("IPCA 2025 = 4,26%", "4,26", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               _veredito(4.26, ipca_2025), "%"),
        _linha("'melhor resultado nominal desde 2018'", "menor desde 2018",
               f"mín. 2019–2024 = {desde_2018.min():.2f} "
               f"(2018: {ipca_dez.loc['2018-12-01']:.2f})",
               "SGS 13522 (fechamentos de dezembro)",
               ("confere (leitura 'desde 2018' = 2019 em diante)" if melhor
                else "não confere"), "%"),
        _linha("Selic de 15,0% ao ano na nota (12/01/2026)", "15,0",
               f"{meta_nota:.2f}", "SGS 432 (vigência em 12/01/2026)",
               _veredito(SELIC_PATAMAR, meta_nota),
               "% a.a."),
        _linha("Focus projetava IPCA 2025 em 4,90% no início de 2025",
               "4,90", f"{focus_490:.2f} (pesquisa {d_focus:%d/%m/%Y})",
               "Focus anual (focus_anuais, IPCA ref. 2025)",
               _veredito(4.90, focus_490), "%"),
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
    queda = meta[(meta.data > "2025-12-31") & (meta.valor < SELIC_PATAMAR)]
    d_1o_corte = queda.data.min() if len(queda) else pd.NaT

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    return pd.DataFrame([
        _linha("[27/01/2025] Selic chega a 15,25% em junho/2025", "15,25",
               f"{jun25:.2f} (em 19/06/2025)", "SGS 432",
               f"{_veredito(15.25, jun25)} — ficou 0,25 abaixo (15,00)", "% a.a."),
        _linha("[27/01/2025] …e permanece nesse patamar até o fim de 2025",
               "15,25 até dez/2025", f"{dez25:.2f} em dez/2025", "SGS 432",
               "confere como direção (patamar alto mantido), não o valor",
               "% a.a."),
        _linha("[27/01/2025] IPCA 2025 = 5,6%", "5,6", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               f"{_veredito(5.6, ipca_2025)} — erro {ipca_2025 - 5.6:+.2f} p.p.", "%"),
        _linha("[27/01/2025] dívida bruta = 81% do PIB em 2025", "81,0",
               f"{dbgg_dez25:.2f}", "SGS 13762 (dez/2025)",
               f"{_veredito(81, dbgg_dez25)} — erro {dbgg_dez25 - 81:+.2f} p.p.", "%"),
        _linha("[27/01/2025] déficit primário = 0,63% do PIB em 2025",
               "0,63", f"{pri_2025:.2f}", "SGS 5793 (dez/2025, + = déficit)",
               f"{_veredito(0.63, pri_2025)} — erro {pri_2025 - 0.63:+.2f} p.p.",
               "%"),
        _linha("[15/09/2025] Selic mantida em 15% nas 3 últimas reuniões "
               "de 2025", "15,00", f"{dez25:.2f}", "SGS 432 (dez/2025)",
               _veredito(SELIC_PATAMAR, dez25),
               "% a.a."),
        _linha("[15/09/2025] 1º corte em janeiro de 2026 (14,75%)",
               "jan/2026",
               f"{d_1o_corte:%d/%m/%Y}" if d_1o_corte == d_1o_corte else "—",
               "SGS 432 (primeira queda abaixo de 15%)",
               "não confere — foi março/2026", ""),
        _linha("[15/09/2025] IPCA 2025 = 4,8%", "4,8", f"{ipca_2025:.2f}",
               "SGS 13522 (dez/2025)",
               f"{_veredito(4.8, ipca_2025)} — erro {ipca_2025 - 4.8:+.2f} p.p.", "%"),
        _linha("[15/09/2025] dívida bruta = 79,80% do PIB em 2025", "79,80",
               f"{dbgg_dez25:.2f}", "SGS 13762 (dez/2025)",
               _veredito(79.8, dbgg_dez25), "%"),
    ])


# ------------------------------------------------------------------ saída / CLI


def verificacao_bresser() -> pd.DataFrame:
    """Recalcula as alegações do artigo de Bresser-Pereira (4/11/2026).

    O artigo é um ENDOSSO à proposta de Lara Resende — não é fonte primária
    dela. Os números de jun/2026 são os mesmos do "Eu Acuso" e são
    reconferidos aqui; o que é novo é a equação da taxa real, a decomposição
    de 7,5%, o ajuste de 4% do PIB, a estimativa de 5% e o dado de 40% de
    estrangeiros (compatível com o NTN-F, não com o estoque total).

    Fontes: RMD (custo médio, detentores, juros apropriados), SGS
    13761/13762/4380/432/dlsp_pib, Focus (Selic 2027) e PIB mensal.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")
    cm = pd.read_parquet(PROCESSADO / "rmd_custo_medio.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    dbgg_s, dpib_s, pib_s = (
        _serie("dbgg_rs"), _serie("dbgg_pib"), _serie("pib_nominal_mensal"))
    pib12 = pib_s.valor.rolling(12).sum()
    pib12.index = pib_s.data.values

    MES = MES_ARTIGO                            # jun/2026 (mês citado)
    dbgg_jun = float(dbgg_s[dbgg_s.data <= MES].valor.iloc[-1]) / 1e6
    dbggpib_jun = float(dpib_s[dpib_s.data <= MES].valor.iloc[-1])
    c = cm[(cm.escopo == "DPF") & (cm.tabela == "estoque 12m")].copy()
    c["data"] = pd.to_datetime(c.data)
    custo_jun = float(c[c.data <= MES].taxa_pct_aa.iloc[-1])
    pib12_jun = float(pib12.asof(MES))
    servico = custo_jun / 100 * dbgg_jun
    servico_pib = servico * 1e6 / pib12_jun * 100
    dlsp_s = _serie("dlsp_pib")
    dlsp_pct = float(dlsp_s[dlsp_s.data <= MES].valor.iloc[-1])
    servico_dlsp = custo_jun * dlsp_pct / 100
    # conta estática do artigo: reprecificar TODO o estoque de 12,68% para
    # 7,5%, sem defasagem — é um limite superior, não uma projeção
    ajuste = (custo_jun - 7.5) / 100 * dbgg_jun * 1e6 / pib12_jun * 100

    # 5% do PIB: juro apropriado da DPF (RMD 2.9) ÷ PIB, na janela 2012–25
    from . import indicadores as ind
    fat = ind.fatores_anuais()
    pib_anual = ind.juros_anuais()[["ano", "pib_mi"]]
    m = fat.merge(pib_anual, on="ano", how="inner")
    m = m[(m.ano >= 2012) & (m.ano <= 2025)].copy()
    if m.empty or m.pib_mi.isna().any() or m.ano.nunique() != len(m):
        raise ValueError("juro apropriado/PIB 2012–25 ausente ou duplicado — "
                         "rode os extratores")
    if 2025 not in set(m.ano):
        raise ValueError("2025 ausente na janela 2012–25 — rode os extratores")
    m["juros_pib"] = m.juros_apropriados_mi / m.pib_mi * 100
    juros_pib_media = float(m.juros_pib.mean())
    juros_pib_acum = float(m.juros_apropriados_mi.sum()
                           / m.pib_mi.sum() * 100)
    juros_total_tri = float(m.juros_apropriados_mi.sum() / 1e6)
    juros_pib_2025 = float(m.loc[m.ano == 2025, "juros_pib"].iloc[0])

    # não-residentes: estoque da DPMFi (RMD 2.7), não o volume negociado
    det = pd.read_parquet(PROCESSADO / "rmd_detentores.parquet")
    det = det[det.detentor == "Não-residentes"].copy()
    det["data"] = pd.to_datetime(det.data)
    if det.empty:
        raise ValueError("RMD 2.7 sem 'Não-residentes' — rode src.extratores.rmd")
    det = det.sort_values("data")
    nr_jun = det[det.data <= MES].iloc[-1]
    nr_ult = det.iloc[-1]
    nr_jun_pct = float(nr_jun.participacao) * 100
    nr_ult_pct = float(nr_ult.participacao) * 100
    nr_ult_data = pd.Timestamp(nr_ult.data)

    # não-residentes por título (RMD 2.8): o NTN-F é o prefixado longo
    # negociado na B3; a participação é de ESTOQUE, não de volume negociado
    det_tit = pd.read_parquet(PROCESSADO / "rmd_detentores_titulo.parquet")
    det_tit["data"] = pd.to_datetime(det_tit.data)
    nr_tit = det_tit[det_tit.detentor == "Não-residente"].copy()
    if nr_tit.empty:
        raise ValueError("RMD 2.8 sem 'Não-residente' — rode src.extratores.rmd")

    def _nr_titulo(titulo: str):
        s = nr_tit[nr_tit.titulo == titulo].sort_values("data")
        if s.empty:
            raise ValueError(f"RMD 2.8 sem '{titulo}' — rode src.extratores.rmd")
        jun = s[s.data <= MES].iloc[-1]
        ult = s.iloc[-1]
        return (float(jun.participacao) * 100, float(ult.participacao) * 100,
                pd.Timestamp(ult.data))

    ntnf_jun, ntnf_ult, ntnf_data = _nr_titulo("NTN-F")
    ltn_jun, ltn_ult, _ = _nr_titulo("LTN")

    # Selic atual e consenso Focus para 2027 (a proposta é 7,5% em 12 meses)
    sel = _serie("meta_selic_copom")
    selic_atual = float(sel.valor.iloc[-1])
    selic_data = pd.Timestamp(sel.data.iloc[-1])
    foc = pd.read_parquet(PROCESSADO / "focus_anuais.parquet")
    fsel = (foc[(foc.indicador == "Selic") & (foc.data_referencia == 2027)
                & (foc.base_calculo == 0)]
            .sort_values("data_pesquisa"))
    if fsel.empty:
        raise ValueError("Focus Selic 2027 ausente — rode src.extratores.focus")
    focus_2027 = float(fsel.media.iloc[-1])
    focus_data = pd.Timestamp(fsel.data_pesquisa.iloc[-1])

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    return pd.DataFrame([
        _linha("Custo médio da dívida, jun/2026 (citado de Lara Resende)",
               "12,68", f"{custo_jun:.2f}", "RMD (DPF, estoque 12m, jun/26)",
               _veredito(12.68, custo_jun), "% a.a."),
        _linha("DBGG, jun/2026", "10,9", f"{dbgg_jun:.2f}",
               "SGS 13761 (jun/26)", _veredito(10.9, dbgg_jun), "R$ tri"),
        _linha("DBGG / PIB, jun/2026", "82,5", f"{dbggpib_jun:.1f}",
               "SGS 13762 (jun/26)", _veredito(82.5, dbggpib_jun), "%"),
        _linha("Serviço = custo × estoque, jun/2026", "1,4",
               f"{servico:.2f}", "custo RMD × SGS 13761 (jun/26)",
               _veredito(1.4, servico), "R$ tri"),
        _linha("Serviço / PIB, jun/2026", "10,5", f"{servico_pib:.1f}",
               "custo × DBGG ÷ PIB 12m (SGS 4380, jun/26)",
               _veredito(10.5, servico_pib), "%"),
        _linha("Serviço c/ dívida líquida", "8,7", f"{servico_dlsp:.1f}",
               "custo RMD × DLSP/PIB (SGS dlsp_pib, jun/26)",
               _veredito(8.7, servico_dlsp), "%"),
        _linha("Equação r = i − π + z: 4,5% = 7,5% − 3% + 2%", "4,5",
               f"{7.5 - 3 + 2:.1f}", "aritmética: 7,5 − 3 + 2",
               "não confere — o resultado é 6,5%, não 4,5%; 4,5% é apenas "
               "7,5 − 3", "%"),
        _linha("Decomposição 3,0% + 2,5% + 2,0% = 7,5%", "7,5",
               f"{3.0 + 2.5 + 2.0:.1f}", "aritmética: 3,0 + 2,5 + 2,0",
               "aritmética confere; 2,5% é crescimento do PIB, não juro "
               "neutro — a decomposição só fecha se 2,5% for lido como juro "
               "real", "%"),
        _linha("Ajuste fiscal de ~4% do PIB", "4,0", f"{ajuste:.2f}",
               "(12,68 − 7,5) × DBGG/PIB (jun/26)",
               f"{_veredito(4.0, ajuste)} — conta estática, sem defasagem "
               "de reprecificação; a incidência 'só rentistas' não é testada",
               "% do PIB"),
        _linha("Rentistas capturam 5% do PIB", "5,0",
               f"{juros_pib_media:.1f} (média 2012–25) | "
               f"{juros_pib_acum:.1f} (acumulado, R$ {juros_total_tri:.2f} tri) "
               f"| {juros_pib_2025:.2f} (2025)",
               "RMD 2.9 (juros apropriados DPF) ÷ PIB; janela 2012–25",
               "magnitude compatível com o total (5,2–5,4%); como residual "
               "'não explicado', não é medível — 5% seria quase todo o juro "
               "total", "% do PIB"),
        _linha("40% dos títulos do governo negociados na Bolsa com "
               "estrangeiros", "40",
               f"NTN-F: {ntnf_jun:.1f} (jun/26) | {ntnf_ult:.1f} "
               f"({ntnf_data:%m/%Y}); LTN: {ltn_jun:.1f} | {ltn_ult:.1f}; "
               f"estoque total: {nr_jun_pct:.1f} | {nr_ult_pct:.1f}",
               "RMD 2.8 (estoque da DPMFi por título, não-residentes); "
               "RMD 2.7 (estoque total)",
               "compatível com o NTN-F — 40,2% em set/26, o prefixado "
               "longo negociado na B3; não com o conjunto NTN-F+LTN "
               "(31,3% em set/26) nem com o estoque total (10,0% em "
               "jun/26); a base 'negociados na Bolsa' não está "
               "especificada", "%"),
        _linha("Selic tenderá a 7,5% em 12 meses", "7,5",
               f"atual {selic_atual:.2f} | Focus 2027 {focus_2027:.2f}",
               f"SGS 432 ({selic_data:%d/%m/%Y}) + Focus "
               f"({focus_data:%d/%m/%Y})",
               "proposta normativa, não projeção — o consenso Focus para "
               "2027 está em 13,04%", "% a.a."),
        _linha("Meta de inflação de 3%", "3,0", "3,0",
               "CMN (meta vigente)", "confere", "%"),
        _linha("Venda de reservas para conter a saída de estrangeiros",
               "—", "—", "sem série de reservas no catálogo",
               "proposta sem dado no projeto — não testável", ""),
        _linha("Efeito neofisheriano (Cochrane)", "—", "—",
               "posição teórica", "não testado no projeto — não é dado", ""),
    ])


def verificacao_lara_nota() -> pd.DataFrame:
    """Recalcula as alegações da nota de Lara Resende (16/11/2026).

    A nota é uma CONTINUAÇÃO da proposta de set/2026 — não uma nova fonte
    primária. O que muda é a forma da regra (intervalo entre a inflação e o
    crescimento nominal, prazo de 2–4 anos, forward guidance) e o que ele
    acrescenta de evidência: as correlações com a Selic e o custo do juro
    sobre empresas e famílias.

    Fontes: SGS 4189 (Selic efetiva mensal), 432 (meta Selic), 5793
    (primário/PIB 12m) e RMD (custo médio do estoque 12m e custo das
    emissões por título). As séries que o artigo cita e o projeto NÃO tem —
    custo das emissões antes de 2021 (o RMD 4.3 usa nova metodologia e só
    publica desde 01/2021), NTN-F 10 anos, contas corporativas, recuperações,
    Ibovespa/CDI, endividamento das famílias e reservas internacionais —
    ficam como "não verificável", não como "falso": falta de série não é
    refutação. Para a ponta longa há uma proxy parcial: o custo das emissões
    de NTN-F em 12 meses (RMD, 2021–2026), que é taxa de emissão primária,
    não a taxa de mercado secundário do papel de 10 anos.
    """
    sg = pd.read_parquet(PROCESSADO / "sgs.parquet")
    cm = pd.read_parquet(PROCESSADO / "rmd_custo_medio.parquet")

    def _serie(nome: str) -> pd.DataFrame:
        d = sg[sg.serie == nome][["data", "valor"]].copy()
        d["data"] = pd.to_datetime(d.data)
        if d.empty:
            raise ValueError(f"série '{nome}' ausente — rode src.extratores.sgs")
        return d.sort_values("data").reset_index(drop=True)

    sel_ef = _serie("selic_mensal_anualizada").set_index("data")["valor"]
    meta = _serie("meta_selic_copom").set_index("data")["valor"]

    # ---- ciclo de alta de 2021: 1,9% -> 14,9% (Selic efetiva mensal)
    ciclo = sel_ef["2020-01-01":"2026-11-30"]
    sel_min, sel_max = float(ciclo.min()), float(ciclo.max())
    d_min, d_max = ciclo.idxmin(), ciclo.idxmax()
    meta_ciclo = meta["2020-01-01":"2026-11-30"]
    meta_min, meta_max = float(meta_ciclo.min()), float(meta_ciclo.max())

    # ---- 2011-2012: 12,5% -> 7,25%
    meta_1112 = meta["2011-08-01":"2012-10-31"]
    m_ini, m_fim = float(meta_1112.iloc[0]), float(meta_1112.iloc[-1])
    d_ini = meta_1112.index[0]
    # data do último corte para 7,25% (não o fim da janela)
    d_fim = meta_1112[meta_1112 == m_fim].index[0]

    # ---- correlações: custo do ESTOQUE 12m × Selic mensal
    cm["data"] = pd.to_datetime(cm.data)
    sel_me = meta.resample("ME").last()

    def _corr(escopo: str, ini: str, fim: str) -> tuple[int, float]:
        x = (cm[(cm.escopo == escopo) & (cm.tabela == "estoque 12m")]
             .sort_values("data").set_index("data")["taxa_pct_aa"]
             .resample("ME").last())
        j = pd.concat([x.rename("custo"), sel_me.rename("selic")],
                      axis=1, sort=True).dropna().loc[ini:fim]
        if len(j) < 12:
            raise ValueError(f"correlação {escopo} {ini}..{fim} com {len(j)} meses")
        return len(j), float(j.corr().iloc[0, 1])

    n_dpmfi, corr_dpmfi = _corr("DPMFi", "2011-12-01", "2026-09-30")
    n_dpf, corr_dpf = _corr("DPF", "2011-12-01", "2026-09-30")
    n_dpmfi_22, corr_dpmfi_22 = _corr("DPMFi", "2011-01-01", "2022-12-31")
    n_dpf_22, corr_dpf_22 = _corr("DPF", "2011-01-01", "2022-12-31")

    # ---- proxy da ponta longa: custo das emissões de NTN-F em 12m
    ntnf = (cm[(cm.escopo == "NTN-F") & (cm.tabela == "emissões 12m")]
            .sort_values("data").set_index("data")["taxa_pct_aa"])
    if ntnf.empty:
        raise ValueError("custo das emissões de NTN-F ausente no RMD")
    ntnf_ini, ntnf_ini_data = float(ntnf.iloc[0]), ntnf.index[0]
    ntnf_max, ntnf_max_data = float(ntnf.max()), ntnf.idxmax()
    j_ntnf = pd.concat([ntnf.resample("ME").last().rename("ntnf"),
                        sel_me.rename("selic")], axis=1, sort=True).dropna()
    n_ntnf, corr_ntnf = len(j_ntnf), float(j_ntnf.corr().iloc[0, 1])

    # ---- custo do estoque nos ciclos citados
    def _custo(escopo: str, data: str) -> float:
        x = cm[(cm.escopo == escopo) & (cm.tabela == "estoque 12m")]
        x = x[x.data <= data].sort_values("data")
        return float(x.taxa_pct_aa.iloc[-1])

    dpmfi_2016 = _custo("DPMFi", "2016-02-29")
    dpmfi_2020 = _custo("DPMFi", "2020-12-31")
    dpmfi_2022 = _custo("DPMFi", "2022-12-31")
    dpf_2016 = _custo("DPF", "2016-01-31")
    dpf_2020 = _custo("DPF", "2020-12-31")
    dpf_2022 = _custo("DPF", "2022-12-31")

    # ---- primário 2025
    pri = _serie("primario_pib_12m")
    pri_2025 = float(pri[(pri.data.dt.year == 2025)
                         & (pri.data.dt.month == 12)].valor.iloc[0])

    def _linha(aleg, artigo, nosso, fonte, status, unidade=""):
        return {"alegacao": aleg, "artigo": artigo, "nosso_valor": nosso,
                "unidade": unidade, "fonte_nosso": fonte, "status": status}

    return pd.DataFrame([
        _linha("Selic no ciclo de alta: 1,9% → 14,9%", "1,9 → 14,9",
               f"{sel_min:.1f} ({d_min:%m/%Y}) → {sel_max:.1f} "
               f"({d_max:%m/%Y}); meta {meta_min:.1f} → {meta_max:.1f}",
               "SGS 4189 (Selic efetiva mensal) + 432 (meta)",
               "confere na série efetiva; na meta, 2,0 → 15,0", "% a.a."),
        _linha("NTN-F 10 anos: 7,5% → perto de 15%", "7,5 → ~15",
               f"proxy: {ntnf_ini:.1f} ({ntnf_ini_data:%m/%Y}) → "
               f"{ntnf_max:.1f} ({ntnf_max_data:%m/%Y})",
               "RMD custo das emissões de NTN-F 12m (proxy); a taxa de "
               "10 anos do Tesouro Direto não está no catálogo",
               "confere (≈) como proxy — é taxa de emissão primária, não a "
               "taxa de mercado secundário do papel de 10 anos", "% a.a."),
        _linha("Correlação 0,95: custo das emissões 12m × Selic, "
               "12/2011–09/2026", "0,95",
               f"{corr_dpmfi:.3f} (DPMFi) | {corr_dpf:.3f} (DPF); "
               f"n={n_dpmfi}",
               "proxy: RMD custo do estoque 12m × SGS 432",
               "não verificável na base do artigo — o RMD 4.3 (custo das "
               "emissões) só publica desde 01/2021, com nova metodologia; a "
               "proxy do estoque (2011–2026) dá 0,84, não 0,95",
               "correlação"),
        _linha("Correlação 0,85: NTN-F 10 anos × Selic, 01/2011–10/2026",
               "0,85",
               f"proxy: {corr_ntnf:.2f} (NTN-F emissões 12m × Selic, "
               f"01/2021–09/2026, n={n_ntnf})",
               "RMD custo das emissões de NTN-F 12m × SGS 432",
               "não verificável na janela do artigo — a janela começa em "
               "01/2011 e a série de 10 anos não está no catálogo; a proxy "
               "de 2021–26 dá 0,93", "correlação"),
        _linha("Custo médio (estoque) acompanhou a Selic, 2011–2022",
               "acompanhou",
               f"corr {corr_dpmfi_22:.3f} (DPMFi) | {corr_dpf_22:.3f} "
               f"(DPF); n={n_dpmfi_22}",
               "RMD custo do estoque 12m × SGS 432",
               "confere (≈) para o estoque; a parte de 'novas emissões' não "
               "é testável antes de 2021 (RMD 4.3 começa em 01/2021)",
               "correlação"),
        _linha("Selic: 12,5% → 7,25% (ago/2011–out/2012)", "12,5 → 7,25",
               f"{m_ini:.2f} ({d_ini:%d/%m/%Y}) → {m_fim:.2f} "
               f"({d_fim:%d/%m/%Y})", "SGS 432 (meta Selic)", "confere",
               "% a.a."),
        _linha("Custo das novas emissões: >14% → <5% (ciclo 2016–2020)",
               ">14 → <5",
               f"estoque: {dpmfi_2016:.1f} → {dpmfi_2020:.1f} (DPMFi) | "
               f"{dpf_2016:.1f} → {dpf_2020:.1f} (DPF)",
               "RMD custo do estoque 12m",
               "não verificável para emissões — o RMD 4.3 só começa em "
               "01/2021; o estoque caiu a 7,3–8,4%, não a <5%", "% a.a."),
        _linha("Custo das novas emissões voltou a >12% no fim de 2022",
               ">12",
               f"estoque: {dpmfi_2022:.1f} (DPMFi) | {dpf_2022:.1f} (DPF) "
               "em dez/22", "RMD custo do estoque 12m",
               "não verificável para emissões — o RMD 4.3 só começa em "
               "01/2021; o estoque ficou em 10,2–10,8%", "% a.a."),
        _linha("Déficit primário 2025: abaixo de 2/3 dos países do FMI; "
               "emergentes 3,9%; avançadas 2,5%",
               "0,43 (Brasil); 3,9; 2,5", f"{pri_2025:.2f} (SGS 5793, dez/25)",
               "SGS 5793; FMI Fiscal Monitor não coletado",
               "o dado do Brasil confere; a comparação internacional não é "
               "verificável com o catálogo", "% do PIB"),
        _linha("Companhias abertas: dívida 4,6× lucro; custo 9% vs 3,5%; "
               "despesa 40% vs 16%; 23% → 43%",
               "4,6× / 9% / 3,5% / 40% / 16% / 23% → 43%", "—",
               "sem série de contas corporativas no catálogo",
               "não verificável com dados do projeto", ""),
        _linha("Investimento: 91% da depreciação (2025), 113% (2021), "
               "149% (EUA)", "91 / 113 / 149", "—",
               "sem série de investimento/depreciação no catálogo",
               "não verificável com dados do projeto", "%"),
        _linha("Recuperações judiciais: 977 (2025), 2.466 empresas, "
               "1.099 (1º sem/2026), agro 30%",
               "977 / 2.466 / 1.099 / 30", "—",
               "sem série Serasa/recuperações no catálogo",
               "não verificável com dados do projeto", ""),
        _linha("Ibovespa 40× vs CDI 103× (07/1994–10/2026); 93 de 268 "
               "janelas", "40× / 103× / 93 de 268", "—",
               "sem série de Ibovespa/CDI no catálogo",
               "não verificável com dados do projeto", ""),
        _linha("Famílias: dívida 50,1% da renda; serviço 29% (ago/2026)",
               "50,1 / 29", "—",
               "sem série de endividamento das famílias no catálogo",
               "não verificável com dados do projeto", "%"),
        _linha("Reservas cambiais + dólares de exportadores > US$ 400 bi",
               ">400", "—", "sem série de reservas internacionais no catálogo",
               "não verificável com dados do projeto", "US$ bi"),
        _linha("Estudo de Dejanir Silva (Purdue, nov/2026)", "—", "—",
               "estudo externo não coletado",
               "não verificável com dados do projeto", ""),
        _linha("Proposta: intervalo [inflação, crescimento nominal], 2–4 "
               "anos, fora só em condições extraordinárias", "—", "—",
               "proposta normativa", "não é dado — registrada como posição",
               ""),
    ])


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
        verificacao_bresser().assign(documento="bresser_lara_resende_2026"),
        verificacao_lara_nota().assign(documento="lara_nota_2026_11"),
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

    print("\n== verificação: artigo Bresser-Pereira (4/11/2026) ==")
    b = verificacao_bresser()
    print(b[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    print("\n== verificação: nota Lara Resende (16/11/2026) ==")
    n = verificacao_lara_nota()
    print(n[["alegacao", "artigo", "nosso_valor", "status"]]
          .to_string(index=False))

    csv, pq, vcsv = salvar()
    print(f"\nok: {csv}\nok: {pq}\nok: {vcsv}")


if __name__ == "__main__":
    main()
