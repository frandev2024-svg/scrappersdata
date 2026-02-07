@echo off
REM Scraper de XNXX (busqueda)

title Scraper XNXX
color 0A

cd /d "%~dp0"

chcp 65001 >nul

echo.
echo ============================================================
echo  SCRAPER XNXX - BUSQUEDA
echo ============================================================
echo.
echo Caracteristicas:
echo  - Recorre grilla de resultados
echo  - Entra a cada video y extrae metadatos
echo  - Guarda xnxx.json en el root del workspace
echo.

set /p PAGES="Cuantas paginas deseas scrapear?: "
if "%PAGES%"=="" set PAGES=1

set /p STARTURL="URL de inicio (Enter = default): "

echo.
echo Iniciando scraper con %PAGES% paginas...

echo.
if "%STARTURL%"=="" (
  python scraper_xnxx.py --max-pages %PAGES% --push
) else (
  python scraper_xnxx.py --max-pages %PAGES% --start-url "%STARTURL%" --push
)

echo.
echo ============================================================
echo  PROCESO COMPLETADO
echo ============================================================
echo.
pause
