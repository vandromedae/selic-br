# Juros e Dívida pública — Brasil (2002–2026)

Análise de dados sobre **quem paga, quem recebe e o que acontece** com o
dispêndio de juros da dívida pública federal brasileira — construída
exclusivamente com **fontes públicas verificáveis**, e uma proposta de
ferramenta web de transparência sobre os rendimentos da dívida.

> **Princípio do projeto:** separar rigorosamente (i) o que os **dados**
> mostram, de (ii) **posições e documentos** (atas, manifestos, declarações).
> Nenhum notebook afirma intenção ou nomeia beneficiários individuais — as
> atas do Copom registram a decisão do Comitê, **sem votos nominais**;
> discursos de diretores têm autor assinado, mas falar de um tema não é
> votar por ele (ver `notebooks/06_documentos.ipynb` e `07_discursos.ipynb`).
> *Revisão do usuário em 8/11/2026: recorte aprovado; a leitura "falar ≠
> defender" está mantida **com revisão mais detalhada marcada para depois**.*

---

## Perguntas e respostas resumidas (com evidência dos notebooks)

### P1 — Os juros altos se justificam? (`notebooks/01_juros_se_justificam.ipynb`)
- A Selic acompanha a inflação **esperada** (Focus), não a realizada — a direção
  do ciclo não é arbitrária. O que é excepcional é a **magnitude**: juro real
  ex ante de 2024–2026 em **média de ~8,8 p.p.** (6,9 em 2024 → 10,1 em 2026)
  — média que desde 2002 só havia sido alcançada em 2002–06, quando a inflação
  caía de dois dígitos. Hoje coexiste com
  IPCA de ~4,6% — **dentro da meta**.
- A regra de Taylor simples pediria ~7,5–9% a.a. para Focus ~5%. O **desvio
  médio 2024–26 (~6,5 p.p.) é o maior entre as janelas comparadas** (2003–14:
  4,9; 2022–23: 5,2 p.p.), mas **não é recorde histórico**: a MM36 chegou a
  9,9 p.p. em fev/2006.
- Atividade (IBC-Br +2–3%) e desemprego em mínimo (5,2–5,3%) não explicam o
  patamar. **Conclusão verificável:** o juro atual é inflação esperada **+
  prêmio institucional adicional** sem contrapeso inflacionário — defender que
  ele "está justificado" é uma posição, não um dado.

### P2 — Quem são os beneficiários? (`notebooks/02_beneficiarios.ipynb`)
- Orientado ao grupo detentor (Anexo 2.7 do RMD, desde 2007): o
  **sistema financeiro** (Instituições Financeiras + Fundos + Seguradoras)
  detém ~50–55% do estoque e é o maior beneficiário estimado do fluxo de juros;
  Previdência ~22–24%; Tesouro Direto (pessoas físicas) ~3%.

- **Aproximação do fluxo por detentor:** participação no estoque em dezembro ×
  juros nominais do ano (SGS 4616) — não é dado oficial; é a melhor
  aproximação possível com dados públicos, válida para tamanho relativo.

- **Lacuna explícita:** identificação intra-grupo (qual banco/fundo, quanto)
  não é pública — o Requerimento 696/2019 da Câmara, que pedia a lista ao
  STN, foi **negado por sigilo bancário**.

### P3 — Os juros amortizam a dívida? (`notebooks/03_juros_amortizam.ipynb`)
- Identidade dos fatores de variação da DPF (Anexo 2.9): `variação do estoque =
  emissão líquida + juros apropriados` — em 2025, R$ 439 bi + R$ 880 bi =
  R$ 1.319 bi. Os resgates **já incluem os juros pagos** (notas 6 e 7 do
  anexo), então **os juros não amortizam a dívida; são a dívida nova**: 67% do
  aumento de 2025 e 88% do acumulado 2012–25 (R$ 5.977 bi dos R$ 6.769 bi)
  foram juros apropriados.
- As emissões anuais giram de 1,9 a 3,8× o juro apropriado (2,2× em 2025) e
  equivalem, em média, a 1,05× os resgates — a máquina de rolagem é muito
  maior que a dívida nova líquida.
- O déficit nominal é dominado por juros; o resultado primário é quase neutro
  na maior parte da série.

### P4 — Os juros geram capital produtivo? (`notebooks/04_banqueiros_capital.ipynb`)
- (a) Rendimento concentrado: setor financeiro ~metade do estoque e do fluxo
  estimado de juros.
- (b) **i > g quase sempre desde 2012** (exceção: choque inflacionário de
  2021–22) e **r > g em termos reais desde 2022** — a dívida se auto-alimenta
  e o capital migra do crédito/investimento para o título soberano sem risco.
- Não há, nos dados públicos de fluxo, **nenhum caminho pelo qual o dispêndio
  de juros se converta em investimento produtivo**: é rolagem (P3) +
  transferência a detentores (P2).

### P5 — O aumento foi proposital? (`notebooks/05_proposital.ipynb`)
- O que os dados permitem: a régua de juro real **alternou de forma dramática
  e reversível** entre mandatos — 9,6% (Lula 1–2) → 4,9% (Dilma/Temer) →
  2,1% (2019–22) → 8,7% (Lula 3). Um país que praticou 2% real em 2021
  praticou 9% em 2025 **sem mudança na estrutura produtiva**: o patamar é
  *escolha de política*, não fatalidade técnica.
- **As médias por mandato escondem os ciclos** (o gráfico 05 agora mostra a
  trajetória mensal): Dilma/Temer foi de 1,4% (jan/13) a 9,2% (out/16, com
  Selic em 14,25%) e só depois caiu; Bolsonaro foi de −2,3% (mar/21) a 8,9%
  (set/22). O aperto atual começou em **março de 2021** e já estava no
  patamar de hoje em **dez/2022 (8,4%)** — a troca de nível não coincide
  com a troca de mandato.
- Dispêndio nominal cresceu ~8,9× entre 2002 e 2025 (R$ 113 bi → R$ 1.008 bi);
  os saltos de % do PIB ocorrem em 2015–16 e 2024–25, ambos com desvio
  acima da regra de Taylor.
- Swaps geraram custo em 8 dos 18 anos (44%, 2008–25) — "imposto cambial"
  recorrente na conta de juros, contratado em diferentes gestões.
- **Não afirmamos intenção aqui**: isso exige documentos (atas, manifestos,
  ofícios) — ver a fase de documentos abaixo.

---

## Fase de documentos — índice das atas do Copom (`notebooks/06_documentos.ipynb`)

**Corpus:** **47 atas públicas da 236ª (20/1/2021) à 282ª (3–4/11/2026)**
(PDFs do BCB, 805 mil caracteres extraídos com `pypdf` — a 282ª foi
incorporada em 11/11/2026 ao rerodar o extrator). Decisão da 282ª:
**manutenção da Selic em 13,75% a.a.**

**O que o índice faz:** inventário de **1.103 trechos citáveis** por tema
(regex → frase ± contexto, com nº da ata e data) — `dados/processado/
copom_trechos.parquet`, regenerável com
`PYTHONPATH=. python -m src.processa.atas_copom`.

**Achados principais (argumentos escritos, não intenção):**
- **2021–22 (aperto 2,00% → 13,75%):** dominam câmbio, mercado financeiro e
  surpresa inflacionária — reação a choques e desancoragem;
- **2023–25:** *risco fiscal* sobe de 15 → 27 frases/ano e *credibilidade*
  de 1 → 44; no topo de 15% (ata 271, 18/6/2025): "a desancoragem das
  expectativas é um fator de desconforto comum a todos os membros";
- **Silêncios documentam:** "swap" aparece **0 vezes** nas 47 atas;
  "juro real ex ante", 1 vez. O prêmio de ~6 p.p. sobre a regra de Taylor
  (P1/P5) é inferido dos dados, **não citado nas atas**;
- **Limitação estrutural:** a ata é decisão do Comitê **sem votos nominais** —
  "quem defendeu o patamar" não tem resposta em documento público do Copom;
  o corpus complementar com **autor assinado** é o dos discursos (abaixo);
  manifestos de entidades do mercado seguem pendentes de coleta.

## Fase de documentos — discursos e apresentações (`notebooks/07_discursos.ipynb`)

**Como o corpus foi obtido:** o portal `bcb.gov.br` é uma SPA sem listagem em
HTML; a API pública interna foi recuperada por engenharia reversa dos bundles
JS (`GET /api/servico/sitebcb/discursos?ano=YYYY`, ver docstring do extrator).
Índice completo: **1.556 discursos (2002–2026)** com URL direta de PDF —
`dados/processado/discursos_indice.csv`.

**Recorte "foco" (ESCOLHA documentada, não o corpus inteiro):** ano ≥ 2021
(mesma janela das atas) + tema monetário no título + autoridade (Presidente/
Diretor) ou divulgação de Relatório → **46 discursos** com texto extraído.

**O que o índice faz:** as **mesmas regex das atas** (`ac.TEMAS`) localizam
frases — **912 trechos citáveis** com autor, data e título
(`dados/processado/discursos_trechos.parquet`), regenerável com
`PYTHONPATH=. python -m src.processa.discursos`.

**Achados principais:**
- **8 autoridades assinam** o recorte (Diogo Guillen 16, Bruno Serra 10,
  Paulo Picchetti 6, Nilton David 5, Fabio Kanczuk 4, Campos Neto 2,
  Fernanda Guardado 2, Paulo Souza 1) — ao contrário das atas;
- **quem assinou já circulou:** os dois autores com mais trechos saíram do
  Banco Central — **Kanczuk** (diretor de Política Econômica até 2021, hoje
  no ASA, fonte do 2º documento do corpus complementar) e **Guillen**
  (diretor de Política Econômica 2022–2025, economista-chefe do Itaú a partir
  de 1/7/2026; conferido em busca externa — CV do BCB e anúncio do banco);
- **dois corpora, dois públicos:** discursos concentram *risco externo*
  (32% vs 21%) e *mercado financeiro* (23% vs 17%); atas concentram
  *risco fiscal* (11% vs 2%) e *credibilidade* (10% vs 2%);
- **juro real ex ante aparece ~10× mais nos discursos** (1,1% vs 0,1%): a
  discussão de prêmio real (o "Taylor +6 p.p." de P1/P5) **ocorre nas
  apresentações, não nas atas** — com trechos citáveis de Kanczuk
  (RTI 3T2021), Picchetti (7/6/2024) e Guillen (RPM/Focus);
- **silêncio consistente:** "swap" = 0 também nos 46 discursos;
- **limitação:** slides de divulgação geram ruído (números de gráfico viram
  "frases") — a leitura é humana; 1 discurso do foco não contém nenhum tema.

**Revisão do usuário (8/11/2026):** recorte aprovado; leitura "falar ≠
defender" mantida com marcação de **revisão mais detalhada posterior**;
ruído de slide aceito como limitação **com a lista entregue para
conferência** (abaixo); coleta de ofícios/Congresso/manifestos segue como
**ainda não coletado**.

### Ruídos e formato — listas para conferência manual

Regras calibradas nos 912 trechos / 46 discursos, geradas por
`PYTHONPATH=. python -m src.processa.discursos`:

- **Ruídos** → `dados/processado/discursos_ruidos.csv` (trecho + url +
  densidade): trecho com cara de tabela/slide quando
  `dens = 1 − letras/caracteres sem espaço > 0,40` → **44 trechos em 25
  discursos** (para referência: 0,45 → 19/11; 0,50 → 10/8). Exemplo real:
  sequência de números de gráfico ("10,2 10,5 9,6 …") virando "frase";
- **Formato** → `dados/processado/discursos_formato.csv` (id, autor,
  formato, motivo): é slide se o título começa com "Apresentação" OU o
  texto tem ≥3 "Fonte:" OU ≥10 marcadores `•▪●·–-` → **45 slides / 1
  prosa** — o único prosa é o **id 1262** (Bruno Serra, 4/3/2021,
  abertura do Workshop LFL).

---

## Fase de documentos — corpus complementar (`src/processa/documentos.py`)

Registro **curado** de documentos de posição (tese explícita + autor
assinado), diferente das ata (decisão coletiva) e dos discursos (inventário
temático). Padrão repetível: cada documento entra com metadados (`DOCS`),
citações **verbatim** (`TRECHOS`, checadas contra o texto bruto — hoje
**25/25**) e uma função própria de verificação aritmética.

**Primeiro documento:** *"Eu Acuso: uma proposta para eliminar os juros
absurdos"* — André Lara Resende (25/9/2026, Substack). Texto bruto arquivado
em `dados/bruto/documentos/eu_acuso_lara_resende_2026-09-25.txt` (corpo +
notas, cortado antes dos comentários).

**Verificação da aritmética com dados do projeto** (SGS + RMD + Estoque da
DPF, mês do artigo = jun/2026) — nada é aceito do documento sem conferência:

| Alegação | Artigo | Nós | Veredito |
| --- | --- | --- | --- |
| Custo médio da dívida, jun/26 | 12,68% a.a. | 12,68 | **confere (exato)** — RMD, DPF estoque 12m |
| DBGG / DBGG-PIB, jun/26 | 10,9 tri / 82,5% | 10,81 tri / 82,0% | confere |
| Serviço = custo × estoque | 1,4 tri / 10,5% PIB | 1,37 tri / 10,4% | confere (aritmética exata com os números dele) |
| Serviço c/ dívida líquida | 8,7% PIB | 8,7% | confere |
| Déficit nominal / PIB | ~10% | 9,51% (SGS 5727) | confere |
| Identidade nominal = juros + primário | — | 9,51 = 8,99 + 0,52 | **fecha (resíduo 0,00)** |
| PIB nominal cresce ~7% a.a. | 7,0% | 7,0% | confere |
| Dívida/PIB sobe ~5,7 p.p./ano | 5,7 | +5,1 | confere (≈) |
| "mais da metade da dívida em LFTs" | >50% | **51,2%** da DPMFi (42,3% da DBGG) | confere — Estoque da DPF, instrumento antes do swap |
| …a mesma alegação pela exposição "após swap" | >50% | 45,9% (RMD Anexo 5.5) | base errada da 1ª checagem (ver nota) |
| Juro apropriado 12m × conta de estoque final | 10,5% | 8,99% (SGS 5760) | conceito diferente, não erro (ver nota) |
| Primário "entre os menores do mundo" (FMI) | — | — | não verificável com dados do projeto |

**Duas correções da revisão** (a primeira checagem errou — documentado para
não repetir):
- **LFT:** o Anexo 5.5 do RMD é *"por exposição — **após swap**"*: reclassifica
  o LFT trocado em swap cambial para "Câmbio" (jun/26: 4567 → 4091 bi; a
  reconciliação fecha exata). A frase dele fala do **instrumento** — pelo
  Estoque da DPF (Anexo 2.1) a LFT era **51,2%** da dívida mobiliária federal
  em jun/26 (50,1% em dez/25, 53,5% em set/26). **Ele está certo.**
- **Serviço:** a conta dele (custo × estoque **final**) é **custo corrente**;
  o SGS 5760 é o juro **apurado em 12 meses** (escopo NFSP: inclui estados e
  swaps). A ponte: 10,4% (estoque final) → 9,7% (estoque médio) → 8,99%
  (apurado). **Os dois números estão certos — conceitos diferentes.** A
  aritmética dele é exata: 12,68 × 10,9 ÷ 13,19 = 10,5; e
  12,68 × DLSP (68,5% do PIB) = 8,7.

Séries novas no catálogo para a conferência: **13761** (DBGG R$),
**13762** (DBGG % PIB), **5727** (resultado nominal/PIB 12m) — 28 séries na
época; hoje são **34**, com as 6 de crédito do teste da Febraban (abaixo).
Convenção SGS 5727/5793: **positivo = déficit** (checado em dez/2020:
+13,34 nominal / +9,24 primário; dez/2021: +4,26 / −0,72).

**Segundo documento:** *"`BC não levará inflação para a meta e cortará juros
mesmo sem espaço`, diz Fabio Kanczuk, do ASA"* — NeoFeed (25/7/2025, entrevista
na Expert XP). Kanczuk foi diretor de Política Econômica do BCB (2019–2021) e
secretário de Política Econômica com Guedes; hoje é diretor de macroeconomia do
ASA. Texto bruto em
`dados/bruto/documentos/kanczuk_asa_2025-07-25.txt` (corpo + entrevista,
cortado antes do rodapé). É a **primeira defesa assinada do patamar** no
corpus — e vem de quem saiu do Banco Central.

| Alegação | Matéria | Nós | Veredito |
| --- | --- | --- | --- |
| Selic em 15% (decisão anterior) | 15% | 15,00 (SGS 432, desde 19/6/2025) | confere |
| "patamar mais alto desde 2006" | — | última vez ≥15%: **jul/2006** (15,25%); máx. depois: 14,75% | **confere** |
| "juro real observado acima de 6% desde 2022" (ex-post) | >6% desde 2022 | sempre ≥6% só desde **11/2024**; mín. 2022–23 = −1,2%; 8 de 24 meses abaixo | não confere como escrito |
| …a mesma alegação (ex-ante: Selic − Focus) | >6% desde 2022 | sempre ≥6% desde **05/2022**; 4 de 24 meses abaixo | confere (≈) — de mai/2022, não de jan/2022 |
| Juro neutro: 8% (ele) / 5% (BC) / 6% (consenso) | — | — | opinião e expectativa — não verificável |
| "Fed deve cortar em outubro" / "Brasil cresce 2%" | — | — | previsões — não verificáveis |

**O que este documento muda no mapa de posições:** as duas críticas se cruzam.
Lara Resende (2026) acusa o Banco Central de **manter juros altos demais**;
Kanczuk (2025) acusa o Banco Central de **cortar antes da hora** — *«É uma
opção para não levar a meta de inflação a sério»*. Os dois, porém, tratam o
nível da Selic como **escolha**, não como consequência técnica: ele propõe
banda de 3%, ele propõe manter 15% por dois a três anos.

### Entidades do mercado — Febraban e ANBIMA (3 documentos, 11 citações)

Textos brutos em `dados/bruto/documentos/`: `febraban_sidney_2026-01-12.txt`,
`anbima_grupo_2025-01-27.txt`, `anbima_grupo_2025-09-15.txt`.

**Febraban — Isaac Sidney, nota assinada (12/1/2026):**

| Alegação | Nota | Nós | Veredito |
| --- | --- | --- | --- |
| IPCA 2025 = 4,26% | 4,26 | 4,26 (SGS 13522) | **confere (exato)** |
| "melhor resultado nominal desde 2018" | — | mín. 2018–2024 = 3,75% | **não confere** |
| Selic de 15,0% ao ano | 15,0 | 15,00 (SGS 432, em 12/1/2026) | confere |
| Focus projetava 4,90% para 2025 no início de 2025 | 4,90 | 4,99 (pesquisa 2/1/2025) | confere (≈) |
| "flexibilização… se não em janeiro, a partir de março" | mar/2026 | 1º corte em **19/3/2026** | **confere** |

**ANBIMA — Grupo Consultivo Macroeconômico (26 economistas de casas
associadas), dois releases:**

| Alegação | Release | Nós | Veredito |
| --- | --- | --- | --- |
| Selic chega a 15,25% em junho/2025 | 27/1/2025 | 15,00 (19/6/2025) | não confere — 0,25 abaixo |
| …e permanece nesse patamar até o fim de 2025 | 27/1/2025 | 15,00 em dez/2025 | confere como direção, não o valor |
| IPCA 2025 = 5,6% | 27/1/2025 | **4,26** | não confere — erro **−1,34 p.p.** |
| Dívida bruta = 81% do PIB em 2025 | 27/1/2025 | 78,64 | não confere — erro −2,36 p.p. |
| Déficit primário = 0,63% do PIB em 2025 | 27/1/2025 | 0,43 | confere (≈) |
| Selic mantida em 15% nas 3 últimas reuniões de 2025 | 15/9/2025 | 15,00 | **confere** |
| 1º corte em **janeiro** de 2026 (14,75%) | 15/9/2025 | 19/3/2026 | não confere — foi março |
| IPCA 2025 = 4,8% | 15/9/2025 | **4,26** | não confere — erro −0,54 p.p. |
| Dívida bruta = 79,80% do PIB em 2025 | 15/9/2025 | 78,64 | confere (≈) |

### Mapa de posições — quem disse o quê sobre o nível da Selic

| Quem | Data | Posição sobre o nível | Documento no corpus |
| --- | --- | --- | --- |
| André Lara Resende (ex-presidente do BCB) | 25/9/2026 | **ataca**: cortar para ~7,5% | `eu_acuso_2026` |
| Fábio Kanczuk (ASA; ex-diretor do BCB) | 25/7/2025 | **defende**: manter 15% por 2–3 anos | `kanczuk_asa_2025` |
| ANBIMA, Grupo Consultivo (26 economistas) | 27/1/2025 | **endossa o aperto**: "justifica uma política monetária mais restritiva" (fiscal) | `anbima_2025_01` |
| ANBIMA, Grupo Consultivo | 15/9/2025 | **registra a defesa interna**: "os juros devem ser mantidos no patamar mais elevado até que haja essa convergência" | `anbima_2025_09` |
| Febraban, Isaac Sidney (presidente; ex-diretor do BCB) | 12/1/2026 | **não endossa o nível**: "não implica concordância com a Selic atual"; mas defende a autonomia do BC e liga a queda dos juros ao fiscal | `febraban_sidney_2026` |

**Três achados do mapa:**

1. **Ninguém no corpus defende o patamar como benéfico a um grupo.** As
   defesas são técnicas (inflação longe do centro da meta) ou institucionais
   (autonomia do BC). A Febraban vai no sentido oposto da hipótese de
   rentistas: *«bancos não precisam e não dependem de juros altos para
   alcançar rentabilidade»*.
2. **As projeções que sustentavam o aperto erraram para cima.** A ANBIMA
   projetou IPCA 2025 em 5,6% (jan) e 4,8% (set) contra **4,26%** real, e
   dívida em 81%/79,8% contra 78,64% — o medo que justificava o nível alto
   não se realizou no tamanho previsto. A projeção de corte em jan/2026
   também falhou (foi março).
3. **As defesas são institucionais e, em boa parte, anônimas.** A ANBIMA
   fala por 26 economistas (o coordenador cita "algumas casas" sem nomes);
   a Febraban assina pelo setor; as atas do Copom não têm voto nominal. Só
   dois documentos têm **pessoa física falando por si**: Lara Resende e
   Kanczuk — e estão em lados opostos.

**Ainda não coletado** (coleta manual, fora dos datasets): ofícios e
comunicações oficiais do BCB/Fazenda defendendo o nível, declarações
individuais de diretores do Copom fora das apresentações, manifestos
setoriais de bancos e investidores, e depoimentos no Congresso (onde a
defesa costuma ser nominal).

### O lado do crédito — o teste da tese da Febraban

A nota da Febraban diz que *"bancos não precisam e não dependem de juros
altos para alcançar rentabilidade"* e, na mesma nota, reconhece que o atual
ambiente *"vem penalizando os tomadores com níveis mais altos de juros e
maior inadimplência"*. Duas frases, dois lados do balanço bancário: os
títulos (o que o banco recebe do Tesouro) e o crédito (o que o banco cobra e
o que não recebe). O catálogo ganhou **6 séries** para medir o segundo lado.

| Série | SGS | média 2021 | média 2026 (jan–set) | último (set/2026) |
| --- | --- | --- | --- | --- |
| Taxa média de juros do crédito livre PF | 20740 | 40,4% a.a. | 61,8% a.a. | **62,4% a.a.** |
| Spread médio do crédito PF | 20785 | 19,4 p.p. | 27,7 p.p. | **28,0 p.p.** |
| Inadimplência da carteira PF | 21084 | 3,0% | **5,6%** | **5,99%** |
| Inadimplência total do SFN | 21082 | — | — | **4,98%** |
| Concessões de crédito livre (R$ mi/mês) | 20634 | 375 mil | 635 mil | 674 mil |

- **O tomador pagou muito mais caro.** A taxa média do crédito livre para
  pessoa física saiu de ~40% a.a. (2021, a menor da série) para **62,4% a.a.**
  em set/2026 — enquanto a Selic ficava em 13,75%.
- **A margem bruta por operação aumentou.** O spread PF subiu de 19,4 para
  **28,0 p.p.** no mesmo período. (Spread = o que o banco cobra menos o que
  ele paga por captar. **Não é lucro**: ainda faltam custo operacional e perda
  com inadimplência.)
- **O custo apareceu na carteira.** A inadimplência de pessoas físicas foi de
  2,89% em dez/2020 para **5,99% em set/2026** — o **segundo maior valor** da
  série (que começa em 03/2011; máx.: 6,04% em ago/2026). Os cinco maiores
  valores de toda a série são de 2026. É exatamente o que a própria Febraban
  descreve na nota.
- Correlação mensal 2011–2026: Selic × taxa média PF **+0,71**; Selic × spread
  **+0,58**; Selic × inadimplência **+0,47**. No ciclo atual, juro alto andou
  junto com crédito caro, spread maior e mais inadimplência.

**E o lado dos títulos?** Aqui o dado contraria a leitura ingênua de
"juros altos enchem o bolso dos bancos": a participação do sistema financeiro
(IF + fundos + seguradoras) na dívida mobiliária **não sobe com a Selic**.
Média em dezembro — **53,3%** nos anos de Selic ≥ 13% (2015, 2016, 2023,
2025) contra **59,3%** nos anos abaixo disso; correlação anual Selic ×
participação = **0,00** (2007–2025). Só as instituições financeiras: 37,8% em
dez/2007 → **32,9%** em dez/2025.

**Lucro do SFN — origem do "R$ 255 bi" (tarefa 2, fechada em 11/11/2026):**
o número oficial usado pela imprensa ("R$ 255 bi de lucro em 2025, todo o
SFN", G1 22/6/2026, Fonte: BCB) **vem do anexo estatístico do REF Out/2026**,
`Gráfico 1.2.3.1 — Evolução do ROE dos segmentos do SFN`: coluna *LL*
(lucro líquido) do SFN, "últimos 12 meses findos em" **dez/2025 =
R$ 254.768.798.944** (ROE 16,3%). Atenção à nota do gráfico: o SFN ali
**exceta os conglomerados prudenciais do Master e do BRB** (comparabilidade).
Série extraída em `dados/processado/sfn_lucro_ll.csv` (2020–2026, trimestral:
119 → 187 → 197 → 193 → 232 → **255** bi em dez de cada ano).
O IFData dá R$ 165,6 bi para 2025 no recorte individual — é outra base
escopo/consolidação, **não é a fonte do 255** (verificado: leituras do portal
não chegam a esse número).

**O que ainda não dá para afirmar:** (1) o detentor "Instituições Financeiras" não
distingue recurso próprio de recurso de terceiros (poupança, CDB, fundos), e a
identificação banco a banco é sigilo (Requerimento 696/2019 negado);
(2) a API do SGS precisa de IPv4 — o `src/extratores/base.py` já ordena o
`getaddrinfo` com IPv4 à frente, sem isso as chamadas estouram timeout.

---

## Reprodução da validação (notebook 00)

Os dados próprios reproduzem o Estudo BNDES nº 67/2026 (*"Atualizando a
decomposição do pagamento de juros nominais, 2002–2025"*) a partir das séries
brutas, com desvio ≤ 0,03 p.p. em todas as células: 2024 juros 8,07% PIB
(BNDES 8,1) / ex-swaps 7,08% (7,1); 2025 7,91% (7,9) / 8,74% (8,7);
swaps +0,98 p.p. (2024) e −0,83 p.p. (2025).

---

## Fontes

| Fonte | Uso | Acesso |
| --- | --- | --- |
| **BCB/SGS** (Sistema Gerenciador de Séries) | 34 séries: juros nominais (4616), swaps caixa (29522), PIB nominal (4380), Selic/IPCA/meta, primário/nominal (5793/5727), DBGG (13761/13762), crédito/inadimplência/spread (20740, 20783, 20785, 21082, 21084, 20634), câmbio, etc. | API pública (exige IPv4) |
| **Tesouro/STN — RMD, Relatório Mensal do Tesouro** | Detentores (Anexo 2.7), custo médio (Anexo 4.1–4.3), composição (5.5), reserva fiscal (6.1) | anexo ZIP via CDN do Tesouro |
| **Tesouro/STN — Fatores de variação e emissões da DPF (Anexo 2 e 2.9)** | estoque, emissões, resgates, juros apropriados | portal (CSV) |
| **Focus / Olinda (BCB)** | medianas anuais de IPCA e Selic; IPCA-12m | Olinda (superdataset) |
| **IBGE SIDRA 6381 (v4099)** | desemprego PNAD-C trimestral (desde 2012) | API SIDRA |
| **BNDES Estudo 67/2026** | referência de decomposição do juro (validação) | PDF |
| **Atas do Copom (BCB)** | 47 atas 2021–2026 (236ª–282ª): índice de temas e trechos citáveis (fase de documentos) | PDFs públicos (probe de URL) |
| **Discursos e apresentações (BCB)** | 1.556 itens 2002–2026; recorte foco 46 com texto (fase de documentos) | API interna pública do portal (engenharia reversa dos bundles JS) |
| **REF Out/2026 — anexo estatístico (BCB)** | origem do "R$ 255 bi de lucro do SFN em 2025" (Gráfico 1.2.3.1, LL 12m); ROE/PLA do SFN 2020–2026 | XLSX manual (`dados_baixados_manualmente/`, não versionado) → `dados/processado/sfn_lucro_ll.csv` |
| **Documentos de posição (corpus complementar)** | "Eu Acuso" de Lara Resende (25/9/2026): 7 citações verbatim + verificação aritmética | Substack (GET público, texto bruto arquivado) |

**Substituições e decisões de fonte** (transparência metodológica):
- A API do Portal da Transparência exige chave de API (pedido cancelado/
  deferido) — substituída por SGS 4616 (juros) + fatores de variação da DPF
  (resgates/emissões);
- Desemprego público só existe de 2012 em diante — a lacuna 2002–2011 é
  **informada, não escondida**;
- O RMD entra em modo manutenção no portal público — o extrator baixa o
  anexo ZIP pelo CDN com descoberta automática (probe) e estado em
  `dados/bruto/rmd/ultimo_anexo.json`.

---

## Estrutura do repositório

```
src/
  extratores/      sgs, tesouro, rmd, focus, ibge, copom, discursos (cache em dados/bruto)
  processa/        indicadores.py — núcleo analítico compartilhado
                   atas_copom.py  — índice de temas/trechos das atas
                   discursos.py   — índice de temas/trechos dos discursos (mesma régua)
                   documentos.py  — corpus de posição: registro curado + verificação
  viz/             graficos.py — estilo, paleta, salvar figuras
notebooks/         00_validação … 07_discursos (executados, com outputs)
dados/             bruto (cache) / processado (parquet)
viz/figs/          PNG das figuras dos notebooks
app/               ferramenta web (Streamlit)
environment.yml    ambiente conda "juros_divida"
```

## Como rodar

```bash
conda env create -f environment.yml   # apenas na primeira vez
conda activate juros_divida

# atualizar dados (cada extrator tem CLI própria)
python -m src.extratores.sgs
python -m src.extratores.tesouro
python -m src.extratores.rmd
python -m src.extratores.focus
python -m src.extratores.ibge
python -m src.extratores.copom     # atas 2021–hoje (descobre a nova ata sozinho)
python -m src.extratores.discursos # índice dos discursos (API interna do portal)
python -m src.extratores.discursos --foco  # baixa + extrai o recorte foco

# processar e reproduzir notebooks
python -m src.processa.indicadores
python -m src.processa.atas_copom  # índice de temas/trechos das atas
python -m src.processa.discursos   # índice de temas/trechos dos discursos
python -m src.processa.documentos  # corpus de posição + verificação aritmética
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

# ferramenta web
streamlit run app/app.py
```

## Limitações declaradas

1. **Fluxo de juros por detentor é estimativa** (participação no estoque ×
   juros) — não existe dado oficial de benefício por credor.
2. **Sem nomes individuais**: sigilo bancário (Req. 696/2019 negado). A
   ferramenta dirá isso em destaque, e indicará o que seria necessário
   para abrir a informação (regulação e titularidade junto aos custodiantes).
3. **Desemprego** só a partir de 2012; gráficos que o usam cobrem 2012–.
4. **2026 é ano incompleto** nas séries de fluxo — o produto marca isso.

## Fase 2 — ferramenta web (`app/`)

Streamlit reaproveitando `src/processa/indicadores.py` e o estilo de
`src/viz/graficos.py`, com aba de **lacunas de transparência** (o que não é
público e por quê). Ver `app/README.md`.
