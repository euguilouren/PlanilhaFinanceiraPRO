@echo off
echo ============================================
echo  INSTALANDO DEPENDENCIAS DO TOOLKIT
echo ============================================
echo.

REM Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Baixe em: https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" na instalacao.
    pause
    exit /b 1
)

echo Python encontrado. Instalando bibliotecas...
echo.
pip install pandas openpyxl numpy

echo.
echo ============================================
echo  INSTALACAO CONCLUIDA!
echo  Agora edite o arquivo rodar.py e execute:
echo     python rodar.py
echo ============================================
pause
