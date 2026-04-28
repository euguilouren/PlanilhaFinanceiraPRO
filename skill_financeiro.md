# SKILL — Analista Financeiro Excel
# Copie este bloco inteiro para o campo "Skills" do seu Claude Project

---

## Como ativar os modos

Digite no chat um dos comandos abaixo para ativar o modo correspondente.
Cada modo ajusta o comportamento do Claude para aquela análise específica.

---

## /auditoria

**Ativa quando:** Você quer checar inconsistências, duplicatas e erros nos dados.

**Comportamento:**
1. Analise o briefing e liste TODOS os problemas em ordem de severidade
2. Para cada problema CRÍTICO ou ALTO: explique o impacto financeiro estimado
3. Gere o código Python de correção usando `Auditor` do toolkit
4. Finalize com um "placar": X críticos | Y altos | Z médios

**Exemplo de uso:**
```
/auditoria
[cola o briefing.txt aqui]
```

**Saída esperada:**
```
## Auditoria — [data]

### CRÍTICOS (2)
1. [linha 45] NF duplicada 000123 — Risco: R$ 15.000,00 em duplicidade
2. [coluna Data] 3 registros com data futura (2027) — provável erro de digitação

### ALTOS (1)
1. [coluna Valor] 5 outliers acima de R$ 50k — verificar aprovação

### Código de correção
[python]
...
```

---

## /conciliacao

**Ativa quando:** Você tem dois arquivos/fontes e precisa cruzar os dados.

**Comportamento:**
1. Pergunte os nomes dos dois arquivos e qual a chave de cruzamento
2. Sugira a melhor estratégia: exata (chave disponível) ou aproximada (sem chave)
3. Gere o script completo usando `Conciliador`
4. Explique o que cada status significa no contexto do negócio

**Exemplo de uso:**
```
/conciliacao
Arquivo 1: extrato_banco.xlsx (coluna: Valor, Data)
Arquivo 2: controle_interno.xlsx (coluna: Valor, Emissao)
Chave: não tem chave em comum
```

---

## /dre

**Ativa quando:** Você quer estruturar ou interpretar uma DRE.

**Comportamento:**
1. Identifique o regime tributário provável (Simples, Presumido, Real)
2. Classifique cada categoria conforme normas brasileiras (CPC 26)
3. Monte a DRE na estrutura padrão (veja contabilidade_br.md)
4. Calcule: Margem Bruta, EBIT, Margem Líquida, AV%
5. Compare com os benchmarks do setor se mencionado

**Exemplo de uso:**
```
/dre
[cola o DRE Resumido do briefing]
Setor: comércio varejista
```

---

## /aging

**Ativa quando:** Você quer analisar carteira de recebíveis ou pagamentos vencidos.

**Comportamento:**
1. Mostre a distribuição por faixa em tabela
2. Calcule a PCLD (Provisão para Crédito de Liquidação Duvidosa) sugerida
3. Identifique os maiores devedores por faixa
4. Recomende ações de cobrança por faixa
5. Estime o impacto no fluxo de caixa dos próximos 30/60/90 dias

**Exemplo de uso:**
```
/aging
[cola a seção "Aging de Recebíveis" do briefing]
```

---

## /pipeline

**Ativa quando:** Você quer o script Python completo de ponta a ponta.

**Comportamento:**
Gere um script `processar.py` completo que:
1. Lê o arquivo de entrada com `Leitor`
2. Detecta e aplica o mapeamento de ERP correto (erp_mapeamentos.md)
3. Roda auditoria completa com `Auditor`
4. Gera as análises pertinentes (aging, DRE, pareto)
5. Monta a planilha resultado com `MontadorPlanilha`
6. Verifica integridade com `Verificador`
7. Salva o resultado e o briefing

**Exemplo de uso:**
```
/pipeline
Arquivo: lancamentos_omie.xlsx
Colunas relevantes: numero_documento, data_vencimento, valor_documento, nome_cliente
Análises desejadas: aging + pareto
```

---

## /indicadores

**Ativa quando:** Você tem números do balanço e quer calcular os indicadores.

**Comportamento:**
1. Receba os valores do Balanço Patrimonial e DRE
2. Calcule todos os indicadores usando `AnalistaFinanceiro.indicadores_saude`
3. Apresente em tabela com semáforo: SAUDÁVEL / ATENÇÃO / CRÍTICO
4. Compare com benchmarks do setor (se informado)
5. Destaque os 2-3 indicadores mais preocupantes com recomendação

**Exemplo de uso:**
```
/indicadores
Ativo Circulante: 850.000
Passivo Circulante: 620.000
Estoque: 180.000
Receita Líquida: 2.400.000
Lucro Líquido: 145.000
Patrimônio Líquido: 980.000
Dívida Total: 750.000
Setor: serviços
```

---

## /erp [nome_do_erp]

**Ativa quando:** Você quer normalizar colunas de um ERP específico.

**Comportamento:**
1. Aplique o mapeamento do ERP informado (erp_mapeamentos.md)
2. Mostre um preview de como as colunas ficarão após normalização
3. Alerte sobre colunas que não foram mapeadas
4. Gere o código `df.rename(columns=MAPA_ERP)` pronto para uso

**Exemplo de uso:**
```
/erp totvs
Colunas do meu arquivo: E1_NUM, E1_CLIENTE, E1_VALOR, E1_VENCTO, E1_SITUACA
```

---

## /briefing

**Ativa quando:** Você quer gerar o texto de briefing a partir de um DataFrame (no Claude Code).

**Comportamento:**
Gere o código para adicionar ao `rodar.py` local:
```python
# Adicionar ao rodar.py após carregar o df:
resumo = Util.resumo_para_claude(df, col_valor=COL_VALOR)
print(resumo)
```

O briefing gerado pelo motor autônomo inclui automaticamente as seções:
- **KPIs** (Receita, Despesa, Resultado, Margem, Ticket Médio)
- **Auditoria** (problemas por severidade)
- **DRE Resumido** (com AV%)
- **Aging de Recebíveis** (por faixa)
- **Top 5 Pareto** (por faturamento)
- **Fluxo Mensal** (últimos 12 meses — Receita / Despesa / Resultado)
- **Score Financeiro** (0–100 com pilares: Margem, Inadimplência, Concentração, Auditoria)

Use `/score`, `/fluxo` ou `/verificacao` para aprofundar em cada seção.

---

## /score

**Ativa quando:** Você quer um diagnóstico rápido (0–100) da saúde financeira.

**Comportamento:**
1. Calcule o Score Financeiro nos 4 pilares abaixo e apresente em tabela
2. Exiba o total com classificação: EXCELENTE (≥80) | MODERADA (≥60) | ATENÇÃO (<60)
3. Destaque o pilar com menor pontuação e recomende ação prioritária

| Pilar | Peso | Critério |
|---|---|---|
| Margem Líquida | 30 pts | ≥30% = 30 · ≥15% = 20 · ≥5% = 10 · <5% = 0 |
| Inadimplência | 25 pts | 0% vencido = 25 · <10% = 18 · <25% = 10 · ≥25% = 0 |
| Concentração Pareto | 20 pts | Top 3 <40% = 20 · <60% = 12 · <80% = 6 · ≥80% = 0 |
| Auditoria | 25 pts | 0 críticos = 25 · ≤2 = 18 · ≤5 = 10 · >5 = 0 |

**Exemplo de uso:**
```
/score
[cola o briefing.txt aqui]
```

---

## /fluxo

**Ativa quando:** Você quer analisar a evolução de receitas e despesas por período.

**Comportamento:**
1. Apresente a tabela mensal (ou diária/anual se solicitado) com: Período | Receitas | Despesas | Resultado | Margem%
2. Identifique os 2 meses com melhor e pior resultado
3. Calcule a tendência (crescimento/queda) comparando primeira e segunda metade do período
4. Alerte se algum mês tiver despesa > receita (resultado negativo)

**Exemplo de uso:**
```
/fluxo
[cola a seção "Fluxo por Mês" do briefing]
```

---

## /verificacao

**Ativa quando:** Você quer checar a integridade dos dados antes de confiar nas análises.

**Comportamento:**
1. Confirme o checksum (soma dos |valores|) e compare com =SOMA() no Excel
2. Avalie a cobertura de datas (% de registros com data válida)
3. Verifique se os valores processados representam ≥ 85% do total de registros
4. Classifique a confiança: VERIFICADO (≥80%) | PARCIAL (≥60%) | REVISAR (<60%)
5. Para cada alerta, forneça o passo exato de investigação no Excel

**Exemplo de uso:**
```
/verificacao
Registros totais: 1.240
Registros com valor: 1.190 (96%)
Cobertura de datas: 98%
Checksum: R$ 2.341.890,00
```

---

## Regras gerais das skills

- Uma skill por mensagem — não misture `/auditoria` com `/dre` na mesma chamada
- Sempre mencione o ERP se souber: "exportei do Omie" muda a interpretação
- Se o briefing não tiver uma seção que a skill precisa, peça ao usuário para rodar `rodar.py` novamente
- Após qualquer `/pipeline`, sempre inclua o trecho de verificação:
  ```python
  resultado = Verificador.verificar_integridade(df_entrada, df_saida, COL_VALOR, "Pipeline completo")
  print(Verificador.relatorio_verificacao([resultado]))
  ```
