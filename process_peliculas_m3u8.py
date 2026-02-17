"""
Script para procesar peliculas.json y agregar m3u8_url a cada servidor
usando el scraper_embed_extractor
"""

import json
import time
import sys
from scraper_embed_extractor import extract_from_embed

INPUT_FILE = 'peliculas.json'
OUTPUT_FILE = 'peliculas.json'  # Sobrescribe el original
BACKUP_FILE = 'peliculas_backup_before_m3u8.json'

def process_peliculas():
    # Cargar el archivo
    print(f"Cargando {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        peliculas = json.load(f)
    
    total_peliculas = len(peliculas)
    total_servers = sum(len(p.get('servers', [])) for p in peliculas)
    print(f"Total películas: {total_peliculas}")
    print(f"Total servidores a procesar: {total_servers}")
    
    # Backup
    print(f"Creando backup en {BACKUP_FILE}...")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(peliculas, f, ensure_ascii=False, indent=2)
    
    # Procesar
    processed_servers = 0
    successful = 0
    failed = 0
    skipped = 0
    
    start_time = time.time()
    
    for i, pelicula in enumerate(peliculas):
        title = pelicula.get('title', 'Sin título')
        servers = pelicula.get('servers', [])
        
        for server in servers:
            embed_url = server.get('embed_url', '')
            
            # Si ya tiene m3u8_url, saltar
            if server.get('m3u8_url'):
                skipped += 1
                processed_servers += 1
                continue
            
            if not embed_url:
                skipped += 1
                processed_servers += 1
                continue
            
            try:
                result = extract_from_embed(embed_url)
                
                if result.get('best_url'):
                    server['m3u8_url'] = result['best_url']
                    successful += 1
                else:
                    server['m3u8_url'] = None
                    server['m3u8_error'] = result.get('error', 'No se encontró URL')
                    failed += 1
                    
            except Exception as e:
                server['m3u8_url'] = None
                server['m3u8_error'] = str(e)
                failed += 1
            
            processed_servers += 1
            
            # Mostrar progreso cada 10 servidores
            if processed_servers % 10 == 0:
                elapsed = time.time() - start_time
                rate = processed_servers / elapsed if elapsed > 0 else 0
                eta = (total_servers - processed_servers) / rate if rate > 0 else 0
                print(f"\r[{processed_servers}/{total_servers}] OK: {successful} | FAIL: {failed} | Skip: {skipped} | ETA: {eta:.0f}s", end='', flush=True)
            
            # Pequeña pausa para no saturar los servidores
            time.sleep(0.1)
        
        # Guardar progreso cada 50 películas
        if (i + 1) % 50 == 0:
            print(f"\n  Guardando progreso ({i+1}/{total_peliculas})...")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(peliculas, f, ensure_ascii=False, indent=2)
    
    # Guardar resultado final
    print(f"\n\nGuardando resultado final en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(peliculas, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"PROCESO COMPLETADO")
    print(f"{'='*60}")
    print(f"Total servidores: {total_servers}")
    print(f"Exitosos: {successful}")
    print(f"Fallidos: {failed}")
    print(f"Saltados: {skipped}")
    print(f"Tiempo total: {elapsed:.1f} segundos")
    print(f"{'='*60}")

if __name__ == '__main__':
    process_peliculas()
