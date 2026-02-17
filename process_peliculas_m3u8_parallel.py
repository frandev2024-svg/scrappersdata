"""
Script PARALELO para procesar peliculas.json y agregar m3u8_url a cada servidor
usando el scraper_embed_extractor con múltiples hilos
"""

import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from scraper_embed_extractor import extract_from_embed

INPUT_FILE = 'peliculas.json'
OUTPUT_FILE = 'peliculas.json'
BACKUP_FILE = 'peliculas_backup_before_m3u8.json'

# Configuración
MAX_WORKERS = 10  # Número de hilos paralelos
SAVE_INTERVAL = 100  # Guardar cada N servidores procesados

# Variables globales para estadísticas
stats_lock = Lock()
stats = {
    'processed': 0,
    'successful': 0,
    'failed': 0,
    'skipped': 0
}

def process_server(server_info):
    """Procesa un servidor individual y retorna el resultado"""
    idx, pelicula_idx, server_idx, server, embed_url = server_info
    
    if not embed_url:
        return (pelicula_idx, server_idx, None, None, 'skipped')
    
    try:
        result = extract_from_embed(embed_url)
        
        if result.get('best_url'):
            return (pelicula_idx, server_idx, result['best_url'], None, 'success')
        else:
            error = result.get('error', 'No se encontró URL')
            return (pelicula_idx, server_idx, None, error, 'failed')
            
    except Exception as e:
        return (pelicula_idx, server_idx, None, str(e), 'failed')

def process_peliculas():
    global stats
    
    # Cargar el archivo
    print(f"Cargando {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        peliculas = json.load(f)
    
    # Crear lista de tareas
    tasks = []
    idx = 0
    for pelicula_idx, pelicula in enumerate(peliculas):
        servers = pelicula.get('servers', [])
        for server_idx, server in enumerate(servers):
            embed_url = server.get('embed_url', '')
            # Saltar si ya tiene m3u8_url
            if server.get('m3u8_url'):
                stats['skipped'] += 1
                continue
            tasks.append((idx, pelicula_idx, server_idx, server, embed_url))
            idx += 1
    
    total_tasks = len(tasks)
    total_servers = sum(len(p.get('servers', [])) for p in peliculas)
    
    print(f"Total películas: {len(peliculas)}")
    print(f"Total servidores: {total_servers}")
    print(f"Servidores a procesar: {total_tasks}")
    print(f"Servidores saltados (ya tienen m3u8): {stats['skipped']}")
    print(f"Hilos paralelos: {MAX_WORKERS}")
    
    # Backup
    print(f"Creando backup en {BACKUP_FILE}...")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(peliculas, f, ensure_ascii=False, indent=2)
    
    if total_tasks == 0:
        print("No hay servidores para procesar.")
        return
    
    print(f"\nIniciando procesamiento paralelo...")
    start_time = time.time()
    last_save = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Enviar todas las tareas
        future_to_task = {executor.submit(process_server, task): task for task in tasks}
        
        for future in as_completed(future_to_task):
            pelicula_idx, server_idx, m3u8_url, error, status = future.result()
            
            # Actualizar el servidor en la lista
            if m3u8_url:
                peliculas[pelicula_idx]['servers'][server_idx]['m3u8_url'] = m3u8_url
                stats['successful'] += 1
            elif status == 'failed':
                peliculas[pelicula_idx]['servers'][server_idx]['m3u8_url'] = None
                peliculas[pelicula_idx]['servers'][server_idx]['m3u8_error'] = error
                stats['failed'] += 1
            elif status == 'skipped':
                stats['skipped'] += 1
            
            stats['processed'] += 1
            
            # Mostrar progreso
            if stats['processed'] % 10 == 0:
                elapsed = time.time() - start_time
                rate = stats['processed'] / elapsed if elapsed > 0 else 0
                eta = (total_tasks - stats['processed']) / rate if rate > 0 else 0
                print(f"\r[{stats['processed']}/{total_tasks}] OK: {stats['successful']} | FAIL: {stats['failed']} | {rate:.1f}/s | ETA: {eta:.0f}s   ", end='', flush=True)
            
            # Guardar progreso periódicamente
            if stats['processed'] - last_save >= SAVE_INTERVAL:
                with stats_lock:
                    print(f"\n  Guardando progreso ({stats['processed']}/{total_tasks})...")
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(peliculas, f, ensure_ascii=False, indent=2)
                    last_save = stats['processed']
    
    # Guardar resultado final
    print(f"\n\nGuardando resultado final en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(peliculas, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"PROCESO COMPLETADO")
    print(f"{'='*60}")
    print(f"Total procesados: {stats['processed']}")
    print(f"Exitosos: {stats['successful']}")
    print(f"Fallidos: {stats['failed']}")
    print(f"Saltados: {stats['skipped']}")
    print(f"Tiempo total: {elapsed:.1f} segundos ({elapsed/60:.1f} minutos)")
    print(f"Velocidad: {stats['processed']/elapsed:.1f} servidores/segundo")
    print(f"{'='*60}")

if __name__ == '__main__':
    process_peliculas()
