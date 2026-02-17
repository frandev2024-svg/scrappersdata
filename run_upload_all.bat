@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo   SUBIR TODOS LOS JSON A GITHUB
echo ======================================
echo.

call .venv\Scripts\activate.bat
python upload_all_github.py %*

echo.
pause
