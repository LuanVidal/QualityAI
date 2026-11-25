@echo off
setlocal
cd /d "%~dp0"

echo [QualityAI] Preparando ambiente Python 3.11...
py -3.11 -m venv .venv
if errorlevel 1 goto :erro

echo [QualityAI] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo Instalacao concluida. Execute iniciar-qualityai.bat.
pause
exit /b 0

:erro
echo.
echo Nao foi possivel concluir a instalacao.
pause
exit /b 1
