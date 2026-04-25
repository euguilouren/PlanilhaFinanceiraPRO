@echo off
setlocal
echo ============================================================
echo  TOOLKIT FINANCEIRO — Build de Executaveis Windows
echo  Powered by Luan Guilherme Lourenco
echo ============================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Baixe em: https://www.python.org/downloads/
    pause & exit /b 1
)

REM Instala dependencias de build
echo [1/4] Instalando dependencias de build...
pip install -r requirements.txt nuitka ordered-set
if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias. & pause & exit /b 1 )

REM Cria pasta de saida
if not exist dist mkdir dist

echo.
echo [2/4] Compilando rodar.exe ...
python -m nuitka ^
    --onefile ^
    --include-package=base_conhecimento ^
    --include-module=toolkit_financeiro ^
    --include-module=relatorio_html ^
    --windows-console-mode=force ^
    --output-filename=rodar.exe ^
    --output-dir=dist ^
    --remove-output ^
    rodar.py
if errorlevel 1 ( echo [ERRO] Falha ao compilar rodar.py & pause & exit /b 1 )

echo.
echo [3/4] Compilando motor.exe ...
python -m nuitka ^
    --onefile ^
    --include-package=base_conhecimento ^
    --include-module=toolkit_financeiro ^
    --include-module=relatorio_html ^
    --windows-console-mode=force ^
    --output-filename=motor.exe ^
    --output-dir=dist ^
    --remove-output ^
    motor_automatico.py
if errorlevel 1 ( echo [ERRO] Falha ao compilar motor_automatico.py & pause & exit /b 1 )

echo.
echo [4/4] Copiando arquivos necessarios para dist\...
copy config.yaml dist\config.yaml >nul
copy index.html  dist\index.html  >nul
copy prompt_sistema.md dist\prompt_sistema.md >nul

echo.
echo ============================================================
echo  BUILD CONCLUIDO!
echo.
echo  Arquivos gerados em dist\:
echo    rodar.exe   — processa um arquivo (sem Python necessario)
echo    motor.exe   — daemon de monitoramento autonomo
echo    config.yaml — edite antes de usar o motor.exe
echo    index.html  — dashboard web (abre no navegador)
echo.
echo  Uso:
echo    rodar.exe minha_planilha.xlsx
echo    motor.exe --once
echo    motor.exe --arquivo minha_planilha.xlsx
echo ============================================================
pause
