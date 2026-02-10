@echo off
REM Scraper de peliculas desde poseidonhd2.co/peliculas
REM Ejecuta: python scraper_poseidon_movies.py con diferentes opciones

title Scraper Peliculas - PoseidonHD2
color 0A

cd /d "%~dp0"

chcp 65001 >nul

:MENU
echo.
echo ============================================================
echo  SCRAPER DE PELICULAS DESDE POSEIDONHD2.CO
echo ============================================================
echo.
echo Selecciona una opcion:
echo.
echo  [1] Peliculas generales (grid principal)
echo  [2] Tendencias de la semana
echo  [3] Tendencias del dia
echo  [4] Por genero (accion, terror, comedia, etc.)
echo  [5] Pelicula individual (URL directa)
echo  [6] URL personalizada
echo  [0] Salir
echo.
set /p OPCION="Opcion: "

if "%OPCION%"=="0" goto :EOF
if "%OPCION%"=="1" goto GENERAL
if "%OPCION%"=="2" goto TENDENCIAS_SEMANA
if "%OPCION%"=="3" goto TENDENCIAS_DIA
if "%OPCION%"=="4" goto GENERO
if "%OPCION%"=="5" goto PELICULA_DIRECTA
if "%OPCION%"=="6" goto URL_CUSTOM
goto MENU

:GENERAL
set URL_ARG=
goto CONFIGURAR

:TENDENCIAS_SEMANA
set URL_ARG=--url "https://www.poseidonhd2.co/peliculas/tendencias/semana"
goto CONFIGURAR

:TENDENCIAS_DIA
set URL_ARG=--url "https://www.poseidonhd2.co/peliculas/tendencias"
goto CONFIGURAR

:GENERO
echo.
echo Generos disponibles: accion, aventura, animacion, ciencia-ficcion, comedia, 
echo crimen, documental, drama, familia, fantasia, guerra, historia, misterio,
echo musica, romance, suspenso, terror, western
echo.
set /p GENERO_SEL="Escribe el genero: "
if "%GENERO_SEL%"=="" goto MENU
set URL_ARG=--url "https://www.poseidonhd2.co/genero/%GENERO_SEL%"
goto CONFIGURAR

:PELICULA_DIRECTA
echo.
echo Ejemplo: https://www.poseidonhd2.co/pelicula/338969/the-toxic-avenger
echo.
set /p PELI_URL="Pega la URL de la pelicula: "
if "%PELI_URL%"=="" goto MENU
set URL_ARG=--url "%PELI_URL%"
set PAGES=1
set MOVIES=1
goto EJECUTAR

:URL_CUSTOM
echo.
echo Pega cualquier URL de poseidonhd2.co
echo.
set /p CUSTOM_URL="URL: "
if "%CUSTOM_URL%"=="" goto MENU
set URL_ARG=--url "%CUSTOM_URL%"
goto CONFIGURAR

:CONFIGURAR
echo.
set /p PAGES="Cuantas paginas deseas scrapear? (default: 5): "
if "%PAGES%"=="" set PAGES=5

set /p MOVIES="Cuantas peliculas deseas scrapear? (Enter = todas): "

:EJECUTAR
echo.
echo Iniciando scraper...
echo.

if "%MOVIES%"=="" (
    set MOVIES_ARG=
) else (
    set MOVIES_ARG=--max-movies %MOVIES%
)

if "%PAGES%"=="" set PAGES=5

python scraper_poseidon_movies.py --max-pages %PAGES% %MOVIES_ARG% %URL_ARG%

echo.
echo ============================================================
echo  PROCESO COMPLETADO
echo ============================================================
echo.
set URL_ARG=
set MOVIES_ARG=
set PAGES=
set MOVIES=
pause
goto MENU
