@echo off
REM Scraper de episodios recientes desde poseidonhd2.co

title Scraper Episodios Recientes - PoseidonHD2
color 0A

cd /d "%~dp0"

echo.
echo ============================================================
echo  SCRAPER DE EPISODIOS RECIENTES DESDE POSEIDONHD2.CO
echo ============================================================
echo.
echo Características:
echo  ✅ Extrae episodios recientes
echo  ✅ Agrega series nuevas automáticamente
echo  ✅ Guarda en episodios_recientes.json
echo  ✅ Actualiza series.json con nuevas series
echo.

REM Pedir número de episodios
set /p EPISODES="¿Cuántos episodios deseas scrapear? (default: 20): "
if "%EPISODES%"=="" set EPISODES=20

echo.
echo Iniciando scraper con %EPISODES% episodios...
echo.

python scraper_recent_episodes.py --max-episodes %EPISODES%

echo.
echo ============================================================
echo  ✅ PROCESO COMPLETADO
echo ============================================================
echo.
pause
