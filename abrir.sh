#!/bin/bash
echo "============================================"
echo " TOOLKIT FINANCEIRO — Abrindo no navegador"
echo "============================================"

# Detectar Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "[ERRO] Python não encontrado."
    exit 1
fi

PORT=8080
echo "Servidor em: http://localhost:$PORT"
echo "Para fechar: pressione Ctrl+C"
echo ""

# Abrir navegador automaticamente
sleep 1 &
(sleep 1.5 && \
  if command -v xdg-open &>/dev/null; then xdg-open "http://localhost:$PORT"; \
  elif command -v open &>/dev/null; then open "http://localhost:$PORT"; fi) &

$PY -m http.server $PORT
