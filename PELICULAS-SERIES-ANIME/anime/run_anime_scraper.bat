@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo   SCRAPER DE ANIME - HENAOJARA
echo ======================================
echo.
echo  1. Extraer desde grid (todas las paginas)
echo  2. Extraer un anime por URL
echo.
set /p opcion="Elige opcion (1 o 2): "

if "%opcion%"=="2" goto :POR_URL

:GRID
echo.
set /p max_animes="¿Cuantos animes deseas extraer? (Enter = TODOS): "
echo.
if "%max_animes%"=="" (
    echo Extrayendo TODOS los animes de todas las paginas...
    python scraper_henaojara_anime.py
) else (
    echo Extrayendo %max_animes% animes...
    python scraper_henaojara_anime.py --max-animes %max_animes%
)
goto :FIN

:POR_URL
echo.
set /p url="Pega la URL del anime: "
echo.
echo Extrayendo: %url%
python scraper_henaojara_anime.py --url %url%

:FIN
echo.
echo ======================================
echo   SCRAPING COMPLETADO
echo ======================================
echo.
echo Archivo generado: ../anime2.json
echo.
pause
