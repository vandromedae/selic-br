"""Catálogo de séries SGS/BCB utilizadas no projeto.

Códigos verificados contra o portal de dados abertos do BCB
(dadosabertos.bcb.gov.br) e contra os valores publicados (jan/2027 = execução).
"""

SERIES_SGS: dict[int, dict[str, str]] = {
    # Política monetária
    432: {"nome": "meta_selic_copom", "desc": "Meta Selic definida pelo Copom (% a.a.)", "freq": "D"},
    11: {"nome": "selic", "desc": "Taxa de juros Selic (% a.a., base 252)", "freq": "D"},
    4189: {"nome": "selic_mensal_anualizada", "desc": "Selic acumulada no mês anualizada (% a.a.)", "freq": "M"},
    # Inflação
    433: {"nome": "ipca", "desc": "IPCA - variação % no mês", "freq": "M"},
    13522: {"nome": "ipca_12m", "desc": "IPCA - acumulado em 12 meses (%)", "freq": "M"},
    188: {"nome": "inpc", "desc": "INPC - variação % no mês", "freq": "M"},
    4466: {"nome": "ipca_nucleo_ms", "desc": "IPCA núcleo médias aparadas com suavização (% mês)", "freq": "M"},
    11426: {"nome": "ipca_nucleo_ms_sem_suv", "desc": "IPCA núcleo médias aparadas sem suavização (% mês)", "freq": "M"},
    # Atividade
    24363: {"nome": "ibcbr", "desc": "IBC-Br (índice, saz. ajustada)", "freq": "M"},
    24364: {"nome": "ibcbr_dessaz", "desc": "IBC-Br dessazonalizado (índice)", "freq": "M"},
    4380: {"nome": "pib_nominal_mensal", "desc": "PIB - valor R$ mês corrente (R$ milhões)", "freq": "M"},
    # Estatísticas fiscais do BCB (abaixo da linha, setor público consolidado)
    4616: {"nome": "juros_mensal", "desc": "Juros nominais - fluxo mensal (R$ milhões)", "freq": "M"},
    4649: {"nome": "primario_mensal", "desc": "Resultado primário - fluxo mensal (R$ milhões)", "freq": "M"},
    4583: {"nome": "nominal_mensal", "desc": "Resultado nominal - fluxo mensal (R$ milhões)", "freq": "M"},
    5760: {"nome": "juros_pib_12m", "desc": "Juros nominais / PIB - acumulado 12 meses (%)", "freq": "M"},
    5793: {"nome": "primario_pib_12m", "desc": "Resultado primário / PIB - acumulado 12 meses (%)", "freq": "M"},
    5727: {"nome": "nominal_pib_12m", "desc": "Resultado nominal NFSP s/ val. cambial / PIB - acum. 12 meses (%)", "freq": "M"},
    # Dívida bruta do governo geral (conferência de aritmética de documentos)
    13761: {"nome": "dbgg_rs", "desc": "Dívida bruta do governo geral - saldo (R$ milhões)", "freq": "M"},
    13762: {"nome": "dbgg_pib", "desc": "Dívida bruta do governo geral / PIB (%)", "freq": "M"},
    4513: {"nome": "dlsp_pib", "desc": "Dívida líquida do setor público / PIB (%)", "freq": "M"},
    4478: {"nome": "dlsp_rs", "desc": "Dívida líquida do setor público (R$ milhões)", "freq": "M"},
    # Derivativos cambiais (swaps) — base do componente "swaps" da decomposição BNDES
    22966: {"nome": "derivativos_liquido", "desc": "Derivativos - resultado líquido mensal (R$ milhões)", "freq": "M"},
    22967: {"nome": "derivativos_ativos", "desc": "Derivativos - ativos (R$ milhões)", "freq": "M"},
    22968: {"nome": "derivativos_passivos", "desc": "Derivativos - passivos (R$ milhões)", "freq": "M"},
    29522: {"nome": "swap_resultado_caixa", "desc": "Operações cambiais do BCB - Swap cambial, resultado caixa (R$ milhões)", "freq": "M"},
    29523: {"nome": "swap_resultado_competencia", "desc": "Operações cambiais do BCB - Swap cambial, resultado competência (R$ milhões)", "freq": "M"},
    29526: {"nome": "bcb_resultado_operacoes_cambiarias", "desc": "Resultado do BCB - operações cambiais (R$ milhões)", "freq": "M"},
    29529: {"nome": "bcb_transferencia_tesouro", "desc": "Resultado do BCB a transferir ao Tesouro - acumulado (R$ milhões)", "freq": "M"},
    # Operações compromissadas (proxy "compromissadas/Selic" - meios de pagamento amplos)
    1839: {"nome": "compromissadas_selic", "desc": "Operações compromissadas/Selic - saldo final do período (R$ milhões)", "freq": "M"},
    # Lado do crédito (o outro lado do balanço bancário) — P2 / tese da Febraban
    20740: {"nome": "taxa_media_pf_livres", "desc": "Taxa média de juros das operações de crédito com recursos livres - PF - Total (% a.a.)", "freq": "M"},
    20783: {"nome": "spread_total", "desc": "Spread médio das operações de crédito - Total (p.p.)", "freq": "M"},
    20785: {"nome": "spread_pf", "desc": "Spread médio das operações de crédito - Pessoas físicas - Total (p.p.)", "freq": "M"},
    21082: {"nome": "inadimplencia_sfn", "desc": "Taxa de inadimplência - Total do SFN (%)", "freq": "M"},
    21084: {"nome": "inadimplencia_pf", "desc": "Inadimplência da carteira de crédito - Pessoas físicas - Total (% da carteira)", "freq": "M"},
    20634: {"nome": "concessoes_livres", "desc": "Concessões de crédito com recursos livres - Total (R$ milhões/mês)", "freq": "M"},
}

# Séries em R$ milhões, convenientes para somas anuais
UNIDADES: dict[str, str] = {
    "juros_mensal": "R$ milhões",
    "primario_mensal": "R$ milhões",
    "nominal_mensal": "R$ milhões",
    "derivativos_liquido": "R$ milhões",
    "swap_resultado_caixa": "R$ milhões",
    "swap_resultado_competencia": "R$ milhões",
    "bcb_resultado_operacoes_cambiarias": "R$ milhões",
    "bcb_transferencia_tesouro": "R$ milhões",
    "compromissadas_selic": "R$ milhões",
    "dlsp_rs": "R$ milhões",
    "pib_nominal_mensal": "R$ milhões",
}
