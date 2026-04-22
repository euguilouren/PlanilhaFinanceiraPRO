@echo off
echo ============================================
echo  TOOLKIT FINANCEIRO — Abrindo no navegador
echo ============================================

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERRO] Python nao encontrado.
        echo Instale em: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PY=python3
) else (
    set PY=python
)

echo Iniciando servidor local na porta 8080...
echo Abrindo navegador em: http://localhost:8080
echo Para fechar: pressione Ctrl+C nesta janela
echo.

REM Abrir navegador apos 2 segundos
start "" timeout /t 2 >nul && start http://localhost:8080

REM Iniciar servidor (fica rodando ate Ctrl+C)
%PY% -m http.server 8080
