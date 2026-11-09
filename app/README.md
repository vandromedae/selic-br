# Ferramenta web — Transparência: juros e dívida pública

Streamlit, 8 abas:

| Aba | Conteúdo |
| --- | --- |
| Visão geral | números-chave, gráfico juros ↔ swaps, tabela de validação BNDES |
| P1 · Os juros se justificam? | Selic vs inflação realizada/esperada, juro real, regra de Taylor |
| P2 · Quem recebe os juros? | detentores do estoque (área), estoque por grupo, **fluxo estimado** |
| P3 · Os juros amortizam a dívida? | cascata do estoque (ano selecionável), fluxos anuais, juros vs primário |
| P4 · Os juros geram capital produtivo? | i vs g (nominal) e r vs g (real), ano a ano |
| P5 · Houve propositalidade? | juro real médio por mandato + fatos verificáveis (sem afirmar intenção) |
| Transparência: lacunas | o que **não** é público (Req. 696/2019, fluxo por credor, desemprego pré-2012, API do portal, swaps) e o que a ferramenta oferece no lugar |
| Fontes e metodologia | tabela de fontes e as 5 regras declaradas |

## Como rodar

```bash
conda activate juros_divida
streamlit run app/app.py
```

Os dados são lidos de `dados/processado/*.parquet` (cache dos extratores).
Para atualizar, rode primeiro os extratores (`python -m src.extratores.<nome>`).

## Princípios de produto

1. **Nada é afirmado sem dado**: todas as premissas estimativas estão
   declaradas na interface (fluxo por detentor, g real aproximado).
2. **Lacunas declaradas, não escondidas** — aba dedicada.
3. **Nomes individuais de credores não aparecem**: não é público
   (Requerimento 696/2019 negado por sigilo bancário). A ferramenta
   recomenda o caminho institucional (ato legal sobre titularidade junto
   aos custodiantes), não inferência por extrapolação.
4. **2026 incompleto** é excluído dos gráficos anuais fechados, com aviso.

## Testes

`streamlit.testing.v1.AppTest` cobre todas as 8 abas sem exceção. Exemplo:

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app/app.py"); at.run()
at.radio[0].set_value("P3 · Os juros amortizam a dívida?"); at.run()
assert not at.exception
```
