@echo off
echo ============================================
echo   Procesando peliculas.json con m3u8
echo   Usando %NUMBER_OF_PROCESSORS% hilos
echo ============================================
echo.

cd /d "%~dp0"

python process_peliculas_m3u8_parallel.py

echo.
echo ============================================
echo   Proceso finalizado
echo ============================================
pause
