#!/usr/bin/env python3
"""
Script para agregar imágenes de poster de TMDB al anime.json
y formatear el JSON correctamente para visualización en GitHub.
Versión optimizada con concurrencia.
"""

import json
import requests
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuración TMDB
TMDB_API_KEY = "201d333198374a91c81dba3c443b1a8e"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Control de progreso
progress_lock = Lock()
processed_count = 0

def get_tmdb_poster(tmdb_id):
    """Obtiene el poster de un anime/series de TMDB"""
    session = requests.Session()
    try:
        # Primero intentamos como TV Show
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY, "language": "es-ES"}
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"{TMDB_IMAGE_BASE}{poster_path}"
        
        # Si no se encuentra como TV, intentamos como película
        url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"{TMDB_IMAGE_BASE}{poster_path}"
                
    except requests.exceptions.RequestException:
        pass
    
    return None

def process_anime(args):
    """Procesa un anime individual"""
    global processed_count
    idx, anime, total = args
    
    # Soportar ambos formatos: tmdb_id o id
    tmdb_id = anime.get("tmdb_id") or anime.get("id")
    title = anime.get("title", "Sin título")
    
    # Actualizar progreso
    with progress_lock:
        processed_count += 1
        sys.stdout.write(f"\r     Procesando {processed_count}/{total}: {title[:40]:<40}")
        sys.stdout.flush()
    
    # Si ya tiene poster completo, saltar
    if anime.get("poster") and anime.get("poster").startswith("http"):
        return idx, None, "skipped"
    
    # Si tiene poster_path, construir URL completa
    if anime.get("poster_path"):
        poster_path = anime.get("poster_path")
        if not poster_path.startswith("http"):
            poster_url = f"{TMDB_IMAGE_BASE}{poster_path}"
        else:
            poster_url = poster_path
        return idx, poster_url, "updated"
    
    # Si no tiene poster_path ni poster, obtener de la API
    if not tmdb_id:
        return idx, None, "skipped"
    
    poster_url = get_tmdb_poster(tmdb_id)
    
    if poster_url:
        return idx, poster_url, "updated"
    else:
        return idx, None, "error"

def main():
    global processed_count
    
    print("=" * 60)
    print("AGREGANDO POSTERS DE TMDB A ANIME.JSON (CONCURRENTE)")
    print("=" * 60)
    
    # Cargar anime.json
    print("\n[1/3] Cargando anime.json...")
    with open("anime.json", "r", encoding="utf-8") as f:
        animes = json.load(f)
    
    total = len(animes)
    print(f"     Se encontraron {total} animes")
    
    # Procesar con ThreadPool (20 workers concurrentes)
    print("\n[2/3] Obteniendo posters de TMDB (20 peticiones concurrentes)...")
    updated = 0
    skipped = 0
    errors = 0
    
    # Preparar argumentos
    args_list = [(i, anime, total) for i, anime in enumerate(animes)]
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_anime, args): args for args in args_list}
        
        for future in as_completed(futures):
            idx, poster_url, status = future.result()
            
            if status == "updated":
                animes[idx]["poster"] = poster_url
                updated += 1
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1
    
    print(f"\n\n     Actualizados: {updated}")
    print(f"     Sin cambios:  {skipped}")
    print(f"     Sin poster:   {errors}")
    
    # Guardar con formato legible para GitHub
    print("\n[3/3] Guardando anime.json formateado...")
    with open("anime.json", "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)
    
    print("     ¡Completado!")
    print("\n" + "=" * 60)
    print("El JSON ahora está formateado para visualizarse en GitHub")
    print("=" * 60)

if __name__ == "__main__":
    main()
