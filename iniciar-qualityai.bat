@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo QualityAI ainda nao foi instalado.
    echo Execute instalar-qualityai.bat primeiro.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
