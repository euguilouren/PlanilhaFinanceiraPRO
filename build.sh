#!/bin/bash
set -e

echo "============================================================"
echo " TOOLKIT FINANCEIRO — Build de Executaveis"
echo " Powered by Luan Guilherme Lourenco"
echo "============================================================"
echo

# Verifica Python
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python3 nao encontrado."
    echo "       Linux: sudo apt install python3 python3-pip"
    echo "       Mac:   brew install python"
    exit 1
fi

# Instala dependencias
echo "[1/4] Instalando dependencias de build..."
pip3 install -r requirements.txt nuitka ordered-set

# Cria pasta de saida
mkdir -p dist

echo
echo "[2/4] Compilando rodar ..."
python3 -m nuitka \
    --onefile \
    --include-package=base_conhecimento \
    --include-module=toolkit_financeiro \
    --include-module=relatorio_html \
    --output-filename=rodar \
    --output-dir=dist \
    --remove-output \
    rodar.py

echo
echo "[3/4] Compilando motor ..."
python3 -m nuitka \
    --onefile \
    --include-package=base_conhecimento \
    --include-module=toolkit_financeiro \
    --include-module=relatorio_html \
    --output-filename=motor \
    --output-dir=dist \
    --remove-output \
    motor_automatico.py

echo
echo "[4/4] Copiando arquivos necessarios para dist/..."
cp config.yaml dist/config.yaml
cp index.html  dist/index.html
cp prompt_sistema.md dist/prompt_sistema.md

echo
echo "============================================================"
echo " BUILD CONCLUIDO!"
echo
echo " Arquivos gerados em dist/:"
echo "   rodar   — processa um arquivo (sem Python necessario)"
echo "   motor   — daemon de monitoramento autonomo"
echo "   config.yaml — edite antes de usar o motor"
echo "   index.html  — dashboard web (abre no navegador)"
echo
echo " Uso:"
echo "   ./dist/rodar minha_planilha.xlsx"
echo "   ./dist/motor --once"
echo "   ./dist/motor --arquivo minha_planilha.xlsx"
echo "============================================================"
