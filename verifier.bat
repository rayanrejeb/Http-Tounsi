@echo off
rem HTTP Tounsi : rejoue toutes les requetes de la demo (sans rien modifier dans la base).
cd /d "%~dp0"
chcp 65001 >nul
title HTTP Tounsi - verification
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo Lance d'abord lancer.bat une fois : il installe tout.
    pause
    exit /b 1
)
.venv\Scripts\python manage.py check_demo
pause
