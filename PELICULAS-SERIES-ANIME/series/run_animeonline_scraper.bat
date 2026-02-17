@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════════════════════╗
echo ║  Scraper AnimeOnline.ninja - Series                 ║
echo ║  (Usa DrissionPage para bypasear Cloudflare)        ║
echo ╚══════════════════════════════════════════════════════╝
echo.

set "VENV_PYTHON=C:\Users\franc\Desktop\SCRAPPERS\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo ERROR: No se encontro el Python del venv en:
    echo   %VENV_PYTHON%
    echo Asegurate de que el entorno virtual existe.
    pause
    exit /b 1
)

set /p URL="Pega la URL de la serie: "
echo.
"%VENV_PYTHON%" "%~dp0scraper_animeonline_series.py" "%URL%"
echo.
pause
