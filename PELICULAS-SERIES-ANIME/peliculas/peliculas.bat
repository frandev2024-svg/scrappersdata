@echo off
REM Scraper de películas con sincronización automática a GitHub y Supabase
REM Ejecuta: python scraper_pelisplushd_movies.py --max-pages 5

title Scraper Películas - Sincronización Automática
color 0A

cd /d "%~dp0"

echo.
echo ============================================================
echo  SCRAPER DE PELÍCULAS CON SINCRONIZACIÓN AUTOMÁTICA
echo ============================================================
echo.
echo Características:
echo  ✅ Extrae películas desde verpeliculasultra.com
echo  ✅ Sincroniza automáticamente a GitHub
echo  ✅ Sincroniza automáticamente a Supabase
echo.

REM Pedir número de páginas
set /p PAGES="¿Cuántas páginas deseas scrapear? (default: 5): "
if "%PAGES%"=="" set PAGES=5

echo.
echo Iniciando scraper con %PAGES% páginas...
echo.

python scraper_pelisplushd_movies.py --max-pages %PAGES%

echo.
echo ============================================================
echo  ✅ PROCESO COMPLETADO
echo ============================================================
echo.
pause
