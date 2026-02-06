@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo   SCRAPER DE ANIME - HENAOJARA
echo ======================================
echo.
echo Este scraper extraerá TODAS las páginas
echo y solo actualizará episodios nuevos.
echo.

set /p max_animes="¿Cuántos animes deseas extraer? (Enter = TODOS): "

echo.
if "%max_animes%"=="" (
    echo Extrayendo TODOS los animes de todas las páginas...
    python scraper_henaojara_anime.py
) else (
    echo Extrayendo %max_animes% animes...
    python scraper_henaojara_anime.py --max-animes %max_animes%
)

echo.
echo ======================================
echo   SCRAPING COMPLETADO
echo ======================================
echo.
echo Archivo generado: ../anime.json
echo.
pause
