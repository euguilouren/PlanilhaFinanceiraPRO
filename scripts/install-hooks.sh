#!/usr/bin/env bash
# install-hooks.sh — Instala os git hooks do projeto localmente.
# Execute uma vez após clonar: bash scripts/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "📦 Instalando git hooks em $HOOKS_DIR ..."

cp "$REPO_ROOT/scripts/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ pre-commit instalado."
echo ""
echo "Para testar manualmente: bash .git/hooks/pre-commit"
echo "Para desinstalar:        rm .git/hooks/pre-commit"
