"""Regras e parâmetros do corpus de discursos — fonte única.

Concentra as regras do recorte editorial (o que entra no corpus e como é
classificado), separadas da lógica de extração/processamento, para
ficarem auditáveis num lugar só. Consumidores:

- `src/extratores/discursos.py` ... recorte "foco" + ano final da varredura
- `src/processa/discursos.py` ..... temas, autor, ruído e forma
- `src/processa/atas_copom.py` .... TEMAS — a MESMA régua de indexação em
  discursos e atas do Copom, para comparar os dois sem tradução entre
  vocabulários
"""

import re

# ---------------------------------------------------------------- recorte "foco"
# Ano ≥ 2021 (janela das atas do Copom) + tema monetário no título +
# autoridade de decisão (Presidente/Diretor) ou divulgação de Relatório.
# É uma ESCOLHA documentada, não o corpus inteiro (ver docstring do
# extrator).

FOCO_TEMA = re.compile(
    r"Copom|Selic|juros|infla|pol[íi]tica monet|Relat[óo]rio de Pol"
    r"|Taylor|expectativ|cen[áa]rios econ", re.I)
FOCO_AUTOR = re.compile(
    r"Presidente|Diretor|Relat[óo]rio de Pol|Divulga[çc][ãa]o", re.I)

# ------------------------------------------------------------------------ temas
# Regexes por expressão literal (não exaustivas): servem para localizar
# FRASES candidatas em cada ata/discurso. Palavras isoladas demais
# (= "fiscal") poluiriam o índice; cada alternativa tem ao menos duas
# palavras de âncora.

TEMAS: dict[str, str] = {
    "juro real": (
        r"juros? reais?\b|juro real"
        r"|aperto monetário em termos reais"
        r"|taxa real de juros?|juros? real neutra"
    ),
    "juro real ex ante": r"\b(?:juros?|selic) rea(?:l|is) ex[- ]ante\b",
    "risco fiscal": (
        r"ris[ck]os? fiscais?"
        r"|domin[âa]ncia fiscal|sustentabilidade fiscal"
        r"|incertezas? fiscal(?:is)?|deteriora[çc][ãa]o fiscal|impasse fiscal"
        r"|pol[íi]tica fiscal|estrat[ée]gia fiscal|quadro fiscal|lado fiscal"
        r"|d[ée]ficit p[úu]blico|d[íi]vida p[úu]blica (l[íi]quida?|bruta)?"
        r"|fracasso fiscal|contas p[úu]blicas|despesa(s)? (p[úu]blica[s]?|obrigat)"
    ),
    "credibilidade": r"credib\w*|desancorad\w*|ancorad\w*",
    "histórico de desencontro": (
        r"desencontro\w*"
        r"|(sequência|recorrência) de surpresas"
        r"|surpresas? altistas|virada[s]? (inesperadas? )?na inflação"
        r"|hist[óo]ricamente (alto|baixo|elevad|intens|importante)"
    ),
    "surpresa inflacionária": (
        r"surpresas? infl"
        r"|acima do esperado|vieram acima|veio acima"
        r"|diferentes do esperado|desconfirm\w*"
    ),
    "câmbio": r"c[âa]mbi\w*",
    # nota: "swap" NÃO aparece em nenhuma das 47 atas 2021–2026 (verificado);
    # tema removido do índice — o derivativo cambial não é citado nos textos.
    "meta de inflação": (
        r"regime de metas|metas? de infla[çc][ãa]o\b"
        r"|meta para a inflação|redor da meta|cumprimento da meta"
        r"|converg[êe]ncia da inflação para as metas|metas fixadas"
    ),
    "mercado financeiro": (
        r"curvas? de juros?"
        r"|derivativos|mercado (de futuros|de derivativos|financeiro)"
        r"|pre[çc]os de (ativos|op[çc][õo]es|swaps)"
        r"|contratos (futuros|a termo)|prêmio \w* de risco"
        r"|Focus\b"
    ),
    "risco externo": (
        r"(cen[áa]rio|economia|condi[çc][õo]es) (internacional|global|externo)"
        r"|guerra\b|ucr[âa]nia|pandemi\w*|tarifa(ços)?|guerras? comercial(?:is)?"
    ),
}

# ------------------------------------------------------- autor (nome no título)
# O campo `autor` do índice mistura nome e cidade; o nome do autor está no
# TÍTULO em dois padrões:
# 1) "Apresentação do Diretor ..., NOME, na ..." (a maioria)
# 2) "Apresentação do Presidente NOME no evento ..." (sem vírgula)

NOME_AUTOR_1 = re.compile(
    r"(?:Apresenta[çc][ãa]o|Discurso|Entrevista)[^.]{0,120}?,\s*"
    r"([A-ZÀ-Þ][\wÀ-ÿ]+(?: [A-ZÀ-Þ][\wÀ-ÿ]+){1,3}),")
NOME_AUTOR_2 = re.compile(
    r"(?:do|da)\s+(?:Presidente|Diretor[a]?)\s+"
    r"([A-ZÀ-Þ][\wÀ-ÿ]+(?: [A-ZÀ-Þ][\wÀ-ÿ]+){1,3})\s+(?:no|na|em|para|sob)")

# ---------------------------------------------------------------- ruído e forma
# Régua de ruído: dens = 1 − letras/caracteres_sem_espaço > limiar (tabela
# ou slide). Calibrada nos 911 trechos: 0,40→44/25, 0,45→19/11, 0,50→10/8.
# A régua de slide é título com "Apresentação" OU ≥3 "Fonte:" OU ≥10
# marcadores (calibrada: 45 de 46 slides, só id 1262 é prosa).

LIMIAR_RUIDO = 0.40
REGEX_FONTE = re.compile(r"\bFonte\s*:", re.IGNORECASE)
MARCADORES_SLIDE = "•▪●·–-"

# ----------------------------------------------------------- varredura de anos
# Ano final da varredura dos discursos (ajustar conforme avança o calendário).
MAX_ANO = 2026
