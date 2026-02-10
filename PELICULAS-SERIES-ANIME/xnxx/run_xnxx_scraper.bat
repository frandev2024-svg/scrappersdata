@echo off
REM Scraper de XNXX (busqueda)

title Scraper XNXX
color 0A

cd /d "%~dp0"

chcp 65001 >nul

:MENU
cls
echo.
echo ============================================================
echo  SCRAPER XNXX - SELECCIONA CATEGORIA
echo ============================================================
echo.
echo  [1] Porno en Espanol (default)
echo  [2] Familial Relations
echo  [3] MILF
echo  [4] Big Cock
echo  [5] Casero
echo  [6] Skinny
echo  [7] Mamada
echo  [8] TODAS las categorias
echo  [9] URL personalizada
echo  [0] Salir
echo.
echo ============================================================
echo.

set /p OPCION="Selecciona una opcion: "

if "%OPCION%"=="0" goto FIN
if "%OPCION%"=="1" set CATEGORIA=porno_espanol
if "%OPCION%"=="2" set CATEGORIA=familial_relations
if "%OPCION%"=="3" set CATEGORIA=milf
if "%OPCION%"=="4" set CATEGORIA=big_cock
if "%OPCION%"=="5" set CATEGORIA=casero
if "%OPCION%"=="6" set CATEGORIA=skinny
if "%OPCION%"=="7" set CATEGORIA=mamada
if "%OPCION%"=="8" set CATEGORIA=ALL
if "%OPCION%"=="9" set CATEGORIA=CUSTOM

if "%CATEGORIA%"=="" (
  echo Opcion invalida
  pause
  goto MENU
)

echo.
set /p PAGES="Cuantas paginas por categoria? [default=3]: "
if "%PAGES%"=="" set PAGES=3

echo.
echo Iniciando scraper...
echo.

if "%CATEGORIA%"=="ALL" (
  echo Scrapeando TODAS las categorias...
  python scraper_xnxx.py --max-pages %PAGES% --all-categories --push
  goto DONE
)

if "%CATEGORIA%"=="CUSTOM" (
  set /p STARTURL="URL de inicio: "
  python scraper_xnxx.py --max-pages %PAGES% --start-url "%STARTURL%" --push
  goto DONE
)

echo Scrapeando categoria: %CATEGORIA%
python scraper_xnxx.py --max-pages %PAGES% --categories %CATEGORIA% --push

:DONE
echo.
echo ============================================================
echo  PROCESO COMPLETADO
echo ============================================================
echo.
set /p OTRA="Deseas scrapear otra categoria? (S/N): "
if /i "%OTRA%"=="S" goto MENU

:FIN
echo.
echo Adios!
pause
