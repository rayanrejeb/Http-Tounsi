@echo off
rem HTTP Tounsi : double-clic pour tout lancer.
cd /d "%~dp0"
chcp 65001 >nul
title HTTP Tounsi
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creation de l'environnement virtuel...
    py -3 -m venv .venv 2>nul || python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo Python introuvable. Installe Python 3.11 ou plus recent depuis python.org, puis relance.
    pause
    exit /b 1
)

.venv\Scripts\python -c "import sys, importlib.util as u; sys.exit(any(u.find_spec(m) is None for m in ('django', 'rest_framework', 'rest_framework_xml', 'graphene_django')))"
if errorlevel 1 (
    echo [2/4] Installation des dependances...
    .venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 ( pause & exit /b 1 )
)

.venv\Scripts\python manage.py migrate --noinput -v 0
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo [3/4] Remise a zero de la demo et nouveaux tokens :
echo.
.venv\Scripts\python manage.py setup_demo
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo [4/4] Serveur sur http://127.0.0.1:8000   -   Ctrl+C pour arreter
echo ------------------------------------------------------------------
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 3; Start-Process 'http://127.0.0.1:8000'"
.venv\Scripts\python manage.py runserver 0.0.0.0:8000

echo.
echo Le serveur s'est arrete. Si le port 8000 etait deja pris, ferme l'autre fenetre du serveur.
pause
