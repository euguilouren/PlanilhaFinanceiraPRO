# Bugs Corrigidos — Sessão de Auditoria

> Resumo de todas as correções aplicadas via PRs #44–#48.
> Base de conhecimento para o próximo agente continuar a partir daqui.

---

## Estado Atual do Repositório

- **Branch principal:** `main`
- **Testes JS (Vitest):** 98 testes passando (eram 73 antes desta sessão)
- **Testes Python (pytest):** 391 passed, 13 skipped
- **Lint (ruff):** 0 erros

---

## PR #44 — fix(r7): 4 bugs

**Arquivo:** `index.html`

| Local | Bug | Fix |
|-------|-----|-----|
| `renderComparativo` ~linha 2893 | `canvas.getContext('2d')` pode retornar `null` em canvas corrompido; passar `null` ao `new Chart()` crasha | Salva em variável `_ctx2d`, retorna se `null` |
| `exportarCSV` ~linha 3468 | Valores iniciando com `=`, `+`, `-`, `@` são interpretados como fórmulas ao abrir CSV no Excel | Função `_csvEsc` prefixa com `'` |
| `toolkit_financeiro.py` — 9 chamadas `groupby()` | Pandas 2.0+ inclui grupos não observados de colunas categóricas sem `observed=True` | Adicionado `observed=True` em todas as 9 chamadas |
| `#claude-api-key` CSS | Campo sem `:focus` visível — viola WCAG 2.4.7 | Adicionado `#claude-api-key:focus` com ring roxo |

---

## PR #45 — fix(r8): null guards DOM + numpy copy + 25 novos testes

**Arquivos:** `index.html`, `motor_automatico.py`, `toolkit_financeiro.py`, + 2 novos arquivos de teste

### index.html — null guards em funções render

| Função | Elemento sem guard | Fix |
|--------|--------------------|-----|
| `renderDRE()` | `dre-content` | `if (!el) return` após getElementById |
| `renderScoreFinanceiro()` | `score-numero`, `score-classificacao`, `score-barra` | Agrupa os 3 e faz `if (!numEl \|\| !claEl \|\| !barra) return` |
| `renderScoreFinanceiro()` | `score-pilares` | Via variável `pilaresEl` com `if (pilaresEl)` |
| `renderVerificacao()` | `card-verificacao`, `verificacao-content` | `if (!card \|\| !cont) return` |
| `renderPareto()` | `pareto-content` (2 lugares) | Cacheado em `elPareto` com guard no topo |

### Python

| Arquivo | Linha | Bug | Fix |
|---------|-------|-----|-----|
| `motor_automatico.py` | 783 | Guard frágil `if receita and math.isfinite(float(receita))` — unreliable para escalar pandas | Troca por `if receita > 0` |
| `motor_automatico.py` | 14 | `import math` ficou órfão após fix acima | Removido |
| `toolkit_financeiro.py` | 1160 | `np.where()` retorna array; mutação `classe[0] = 'A'` sem `.copy()` pode falhar em arrays read-only | Adicionado `.copy()` |

### Novos testes JS

| Arquivo | Testes | Função coberta |
|---------|--------|----------------|
| `tests/js/construirDRE.test.js` | 11 | `construirDRE` — zero cobertura antes |
| `tests/js/calcularSazonalidade.test.js` | 14 | `calcularSazonalidade` — zero cobertura antes |

---

## PR #46 — fix(r9): ValueError guard em relatorio_html

**Arquivo:** `relatorio_html.py` — método `_secao_fluxo()`

**Bug:** `pd.notna()` protege contra `None`/`NaN` mas não contra strings inválidas (ex: `"abc"`). Se qualquer célula contiver valor string não-numérico, `float("abc")` lança `ValueError` e crasha a geração do relatório HTML.

**Valores afetados:** `Resultado_RS`, `Resultado_Pct`, `NFs_Receita`, `NFs_Despesa`

**Fix:** Pré-calcula `res`, `pct`, `nfs_rec`, `nfs_desp` com `try/except (ValueError, TypeError)` — fallback `0.0` / `0`.

---

## PR #47 — fix(r10): None guard + NaN guard

**Arquivos:** `fraude_detector.py`, `toolkit_financeiro.py`

| Arquivo | Linha | Bug | Fix |
|---------|-------|-----|-----|
| `fraude_detector.py` | 55–56 | `_e_feriado(None)` crasha com `AttributeError: 'NoneType' has no attribute 'strftime'` | `if d is None: return False` |
| `toolkit_financeiro.py` | 1472 | `str_lens.quantile(0.95)` retorna `np.nan` em Series com só NaN; `int(np.nan)` crasha com `ValueError` | `q95 = ...; int(q95) if pd.notna(q95) else 10` |

---

## PR #48 — fix(r11): MontadorPlanilha guards (CI em andamento)

**Arquivo:** `toolkit_financeiro.py` — classe `MontadorPlanilha`

| Método | Linha | Bug | Fix |
|--------|-------|-----|-----|
| `adicionar_formula_coluna` | 1586 | Guard apenas em `_aba_meta`, não em `wb.sheetnames` — `KeyError` se aba foi removida do workbook | `if nome_aba not in self._aba_meta or nome_aba not in self.wb.sheetnames` |
| `salvar` | 1672 | `wb.save(caminho)` sem try/except — crash silencioso em path inválido ou sem permissão | `try/except (OSError, PermissionError)` com mensagem descritiva |
| `verificar_formulas_planilha` | 1723 | `load_workbook(caminho_xlsx)` fora do `try` — `FileNotFoundError` não capturado | Move para dentro do `try`; retorna `dict` de erro em vez de crashar |

---

## Áreas Auditadas Sem Bugs

As seguintes áreas foram verificadas e não apresentam bugs confirmados:

**JavaScript (`index.html`):**
- `calcularFluxoPeriodo`, `calcularAntiFraude`, `calcularScoreFinanceiro`, `calcularKPIsComparativo`
- `analisarComClaude` (fetch + error handling)
- `exportarJSON`, `exportarCSV`, `exportarXLSX`
- Drag & Drop event listeners
- `esc()`, `toNum()`, `toDate()`, `fmtBRL()`
- `auditoria()`, `calcularAging()`, `calcularKPIs()`, `calcularPareto()`
- `calcularProjecao()`, `calcularSazonalidade()`, `construirDRE()`

**Python:**
- `base_conhecimento/__init__.py` — todos os 20 ERPs com chaves corretas
- `scripts/obfuscar_html.py` — I/O, encoding, subprocess com timeout
- `fraude_detector.py` — `_primeiro_digito`, `anomalias_temporais`, `_benford`, `outliers_por_entidade`, `concentracao`, `fracionamento`
- `toolkit_financeiro.py` — `indicadores_saude`, `ticket_medio`, `orcado_vs_realizado`
- Todos os imports dos arquivos de teste

---

## Sugestões para Próximo Agente

1. **Testes Python faltando:** `toolkit_financeiro.MontadorPlanilha` não tem testes de unidade
2. **Warning pendente:** `fraude_detector.py:400` — `pd.to_datetime` sem `format=` explícito (UserWarning, não erro)
3. **Cobertura de testes JS:** `calcularFluxoPeriodo`, `calcularAntiFraude`, `calcularScoreFinanceiro` ainda sem testes
4. **Encoding explícito:** Alguns `open()` em Python sem `encoding='utf-8'` explícito
