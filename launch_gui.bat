@echo off
title SonicForge - AI Media Arsenal
cd /d "%~dp0"
python main.py gui
if %errorlevel% neq 0 (
    echo.
    echo [!] Une erreur est survenue lors du lancement de SonicForge.
    pause
)
