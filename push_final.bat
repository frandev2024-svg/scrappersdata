@echo off
REM Cierra cualquier editor abierto
taskkill /F /IM vim.exe >nul 2>&1
taskkill /F /IM nano.exe >nul 2>&1
taskkill /F /IM git.exe >nul 2>&1

timeout /t 2

REM Cambia al directorio
cd /d "c:\Users\franc\Desktop\SCRAPPERS"

REM Limpia el estado de git
git reset --hard HEAD
timeout /t 1

REM Trae cambios remotos
git fetch origin
timeout /t 1

REM Sincroniza con remote
git reset --hard origin/master
timeout /t 1

REM Agrega el archivo
git add PELICULAS-SERIES-ANIME\peliculas.json
timeout /t 1

REM Hace commit
git commit -m "Add: peliculas.json with 47 movies from verpeliculasultra.com"
timeout /t 1

REM Hace push
git push -u origin master
if errorlevel 1 (
    echo.
    echo Intentando force push...
    git push -f -u origin master
)

echo.
echo Estado final:
git log --oneline -3

pause
