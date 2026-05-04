#!/usr/bin/env python3
"""
auto_review.py — Análise automática de bugs no index.html via Claude API.

Uso:
  ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_review.py

Saída:
  - Linhas prefixadas com [BUG] para cada bug encontrado
  - Aplica patches diretos no index.html quando possível
  - Exit code 0 = sem bugs / bugs não-críticos corrigidos
  - Exit code 1 = erro de API ou arquivo não encontrado
"""

import os
import sys
import re
import json
import pathlib
import anthropic

ROOT = pathlib.Path(__file__).parent.parent
HTML = ROOT / "index.html"

SYSTEM_PROMPT = """\
Você é um auditor de código especializado em JavaScript financeiro single-page.
Analise o index.html fornecido e identifique bugs reais — não melhorias estéticas.

Foque em:
1. Bugs de lógica (cálculos errados, condições invertidas, edge cases numéricos)
2. Inconsistências entre módulos (calcular X mas renderizar Y)
3. Vulnerabilidades XSS (innerHTML sem esc(), template literals com dados externos)
4. Problemas de compatibilidade cross-browser (APIs deprecated, DOM manipulation)
5. Memory leaks (Chart.js não destruído, event listeners acumulados, blob URLs)
6. Erros de estado global (mutação indevida, stale closures)

Para cada bug encontrado, responda EXCLUSIVAMENTE no formato JSON abaixo.
Não inclua explicações fora do JSON. Não inclua bugs já corrigidos.

{
  "bugs": [
    {
      "id": "BUG_001",
      "severidade": "CRÍTICA|ALTA|MÉDIA|BAIXA",
      "linha": 123,
      "descricao": "Descrição objetiva do problema",
      "codigo_atual": "trecho exato do código com o bug (máx 120 chars)",
      "codigo_corrigido": "trecho corrigido pronto para substituição",
      "pode_aplicar_patch": true
    }
  ],
  "resumo": "Texto breve com total de bugs por severidade"
}

Se não encontrar bugs, retorne: {"bugs": [], "resumo": "Nenhum bug encontrado."}
"""


def carregar_html() -> str:
    if not HTML.exists():
        print(f"[ERRO] Arquivo não encontrado: {HTML}", file=sys.stderr)
        sys.exit(1)
    content = HTML.read_text(encoding="utf-8")
    # Envia apenas as seções de script (analise.js + app.js) para reduzir tokens
    # mantendo numeração de linhas via comentários
    linhas = content.splitlines()
    trecho = []
    em_script = False
    for i, linha in enumerate(linhas, 1):
        if "<script" in linha:
            em_script = True
        if em_script:
            trecho.append(f"{i:04d}| {linha}")
        if "</script>" in linha:
            em_script = False
    return "\n".join(trecho)


def analisar(client: anthropic.Anthropic, codigo: str) -> dict:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Analise este código JavaScript extraído do index.html "
                    "(números de linha preservados no prefixo NNNN|):\n\n"
                    f"```javascript\n{codigo}\n```"
                ),
            }
        ],
    )
    texto = msg.content[0].text.strip()
    # Extrai JSON mesmo que o modelo adicione markdown ao redor
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        raise ValueError(f"Resposta inesperada da API:\n{texto[:500]}")
    return json.loads(match.group())


def aplicar_patch(bug: dict) -> bool:
    """Aplica substituição exata no index.html. Retorna True se aplicado."""
    atual = bug.get("codigo_atual", "").strip()
    corrigido = bug.get("codigo_corrigido", "").strip()
    if not atual or not corrigido or atual == corrigido:
        return False
    conteudo = HTML.read_text(encoding="utf-8")
    if atual not in conteudo:
        return False
    novo = conteudo.replace(atual, corrigido, 1)
    HTML.write_text(novo, encoding="utf-8")
    return True


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERRO] ANTHROPIC_API_KEY não definida.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("🔍 Carregando index.html...")
    codigo = carregar_html()
    linhas_total = HTML.read_text(encoding="utf-8").count("\n")
    print(f"   {linhas_total} linhas | {len(codigo)} chars de JS enviados para análise\n")

    print("🤖 Consultando Claude API...")
    try:
        resultado = analisar(client, codigo)
    except Exception as e:
        print(f"[ERRO] Falha na API: {e}", file=sys.stderr)
        sys.exit(1)

    bugs = resultado.get("bugs", [])
    resumo = resultado.get("resumo", "")

    print(f"📋 Resumo: {resumo}\n")

    if not bugs:
        print("✅ Nenhum bug encontrado.")
        return

    corrigidos = 0
    nao_aplicados = 0

    for bug in bugs:
        sev = bug.get("severidade", "?")
        bid = bug.get("id", "?")
        linha = bug.get("linha", "?")
        desc = bug.get("descricao", "")
        pode = bug.get("pode_aplicar_patch", False)

        print(f"[BUG] [{sev}] {bid} (linha {linha}): {desc}")

        if pode:
            if aplicar_patch(bug):
                print(f"       ✅ Patch aplicado automaticamente.")
                corrigidos += 1
            else:
                print(f"       ⚠  Patch não pôde ser aplicado (trecho não encontrado).")
                nao_aplicados += 1
        else:
            print(f"       📌 Requer revisão manual.")
            nao_aplicados += 1
        print()

    print("─" * 60)
    print(f"Total: {len(bugs)} bug(s) | {corrigidos} corrigidos automaticamente | {nao_aplicados} para revisão manual")

    if corrigidos > 0:
        print(f"\n✏  index.html modificado — {corrigidos} patch(es) aplicado(s).")


if __name__ == "__main__":
    main()
