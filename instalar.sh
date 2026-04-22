#!/bin/bash
echo "============================================"
echo " INSTALANDO DEPENDENCIAS DO TOOLKIT"
echo "============================================"

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python3 nao encontrado."
    echo "Mac:   brew install python"
    echo "Linux: sudo apt install python3 python3-pip"
    exit 1
fi

echo "Python encontrado: $(python3 --version)"
echo ""
echo "Instalando bibliotecas..."
pip3 install pandas openpyxl numpy

echo ""
echo "============================================"
echo " INSTALACAO CONCLUIDA!"
echo " Edite o rodar.py e execute:"
echo "    python3 rodar.py"
echo "============================================"
