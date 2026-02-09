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
echo Subiendo cambios a GitHub...
pushd "%~dp0\..\.."
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo No se detecto un repositorio git. Saltando push.
  popd
) else (
  git add episodios_recientes.json >nul 2>nul
  git diff --cached --quiet
  if errorlevel 1 (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set TS=%%i
    git commit -m "Update episodios_recientes.json %TS%"
    git push
  ) else (
    echo No hay cambios nuevos para commitear.
  )
  popd
)

echo.
echo ============================================================
echo  ✅ PROCESO COMPLETADO
echo ============================================================
echo.
pause
