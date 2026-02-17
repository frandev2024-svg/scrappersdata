@echo off
chcp 65001 >nul
echo ========================================
echo    Subidor de Canales a GitHub
echo ========================================
echo.

cd /d "%~dp0"
python upload_canales_github.py

echo.
pause
