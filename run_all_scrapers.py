import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Lista de scrapers principales a ejecutar (ruta relativa al workspace root)
SCRAPERS = [
    # Películas
    os.path.join("PELICULAS-SERIES-ANIME", "peliculas", "scraper_poseidon_movies.py"),
    # Series
    os.path.join("PELICULAS-SERIES-ANIME", "series", "scraper_poseidon_series.py"),
    # Episodios recientes
    os.path.join("PELICULAS-SERIES-ANIME", "series", "scraper_recent_episodes.py"),
    # Anime (Henaojara)
    os.path.join("PELICULAS-SERIES-ANIME", "anime", "scraper_henaojara_anime.py"),
    # Partidos (incluye extracción de m3u8)
    "scraper_partidos.py",
    # Puedes agregar más scrapers aquí si lo deseas
]

def run_scraper(script_path):
    """Ejecuta un scraper y retorna el resultado."""
    try:
        print(f"\n--- Ejecutando: {script_path} ---")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=3600)
        print(f"--- Fin {script_path} ---\n")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"[ERROR] {script_path}:\n{result.stderr}")
        return (script_path, result.returncode)
    except Exception as e:
        print(f"[EXCEPTION] {script_path}: {e}")
        return (script_path, -1)

def main():
    print("="*60)
    print("EJECUTANDO TODOS LOS SCRAPERS EN PARALELO")
    print("="*60)
    workspace = os.path.dirname(os.path.abspath(__file__))
    # Ejecutar todos los scrapers en paralelo
    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as executor:
        futures = [executor.submit(run_scraper, os.path.join(workspace, s)) for s in SCRAPERS]
        for future in as_completed(futures):
            script, code = future.result()
            print(f"[RESULTADO] {script}: {'OK' if code == 0 else 'ERROR'}")

    print("\nTodos los scrapers han terminado.")
    # Subir resultados a GitHub automáticamente
    upload_script = os.path.join(workspace, "upload_all_github.py")
    if os.path.exists(upload_script):
        print("\nSubiendo archivos JSON a GitHub...")
        result = subprocess.run([sys.executable, upload_script], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"[ERROR] Subida a GitHub: {result.stderr}")
    else:
        print("No se encontró upload_all_github.py para subir los archivos.")

if __name__ == "__main__":
    main()