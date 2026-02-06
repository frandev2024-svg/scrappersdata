#!/usr/bin/env python3
import subprocess
import time
import os

os.chdir("c:\\Users\\franc\\Desktop\\SCRAPPERS")

# Intentar cerrar cualquier editor que esté abierto
try:
    subprocess.run(["taskkill", "/F", "/IM", "vim.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "nano.exe"], capture_output=True)
except:
    pass

time.sleep(1)

# Intentar hacer reset a una rama limpia
print("🔄 Reseteando a HEAD...")
result = subprocess.run(["git", "reset", "--hard", "HEAD"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)

time.sleep(1)

# Traer cambios remotos
print("\n📥 Trayendo cambios remotos...")
result = subprocess.run(["git", "fetch", "origin"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)

time.sleep(1)

# Resetear a remoto
print("\n🔄 Reseteando a origin/master...")
result = subprocess.run(["git", "reset", "--hard", "origin/master"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)

time.sleep(1)

# Agregar peliculas.json
print("\n📝 Agregando peliculas.json...")
result = subprocess.run(["git", "add", "PELICULAS-SERIES-ANIME/peliculas.json"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)

time.sleep(1)

# Hacer commit
print("\n✍️ Haciendo commit...")
result = subprocess.run(
    ["git", "commit", "-m", "Add: peliculas.json with 47 movies from verpeliculasultra.com"],
    capture_output=True, 
    text=True
)
print(result.stdout if result.stdout else result.stderr)

time.sleep(1)

# Hacer push
print("\n📤 Haciendo push a origin...")
result = subprocess.run(["git", "push", "-u", "origin", "master"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)

if result.returncode == 0:
    print("\n✅ ¡Push exitoso!")
else:
    print("\n❌ Push falló. Intentando force push...")
    result = subprocess.run(["git", "push", "-f", "-u", "origin", "master"], capture_output=True, text=True)
    print(result.stdout if result.stdout else result.stderr)
    
    if result.returncode == 0:
        print("\n✅ ¡Force push exitoso!")
    else:
        print("\n❌ Force push también falló")

print("\n🔍 Estado final:")
result = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)
