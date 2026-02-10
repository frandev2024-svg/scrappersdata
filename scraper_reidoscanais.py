#!/usr/bin/env python3
"""
Scraper para extraer canales de https://reidoscanais.io/canais
Usa la API directa: https://api.reidoscanais.io/channels
Extrae información de los canales y los agrega a canales.json
Si un canal ya existe, agrega la URL como servidor adicional
"""

import json
import re
import os
import requests

# Configuración
API_URL = "https://api.reidoscanais.io/channels"
CANALES_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canales.json")


def normalize_name(name):
    """Normaliza el nombre para comparación"""
    if not name:
        return ""
    # Quitar espacios extra, convertir a minúsculas, quitar caracteres especiales
    normalized = re.sub(r'[^a-z0-9]', '', name.lower())
    return normalized


def generate_id(name, category, existing_ids):
    """Genera un ID único para el canal"""
    # Normalizar nombre para el ID
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    clean_category = re.sub(r'[^a-zA-Z0-9]', '', category.lower()) if category else 'general'
    
    # Encontrar el siguiente número disponible
    base_id = f"{clean_name}_{clean_category}"
    counter = 1
    
    # Buscar el número más alto existente para este patrón
    for existing_id in existing_ids:
        if existing_id.startswith(f"{clean_name}_"):
            match = re.search(r'_(\d+)$', existing_id)
            if match:
                num = int(match.group(1))
                if num >= counter:
                    counter = num + 1
    
    return f"{base_id}_{counter}"


def load_existing_channels():
    """Carga los canales existentes del archivo JSON"""
    if os.path.exists(CANALES_JSON_PATH):
        try:
            with open(CANALES_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Error al cargar {CANALES_JSON_PATH}, creando lista vacía")
            return []
    return []


def save_channels(channels):
    """Guarda los canales en el archivo JSON"""
    with open(CANALES_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)
    print(f"Guardados {len(channels)} canales en {CANALES_JSON_PATH}")


def find_existing_channel(channels, name, slug=None):
    """Busca un canal existente por nombre o slug"""
    normalized_name = normalize_name(name)
    
    for i, channel in enumerate(channels):
        # Comparar por nombre normalizado
        if normalize_name(channel.get('name', '')) == normalized_name:
            return i, channel
        
        # Comparar por slug en la URL del iframe
        if slug:
            iframe_url = channel.get('iframe_url', '')
            if f"rdcanais.top/{slug}" in iframe_url or f"rdcanais.top/embed/?id={slug}" in iframe_url:
                return i, channel
    
    return None, None


def add_url_to_channel(channel, new_url):
    """Agrega una URL al canal si no existe ya"""
    try:
        # Parsear las URLs existentes
        existing_urls = json.loads(channel.get('iframe_url', '[]'))
    except json.JSONDecodeError:
        existing_urls = []
    
    # Agregar la nueva URL si no existe
    if new_url not in existing_urls:
        existing_urls.append(new_url)
        channel['iframe_url'] = json.dumps(existing_urls)
        return True
    return False


def map_category(category_pt):
    """Mapea categorías del portugués al español"""
    category_map = {
        'entretenimento': 'Entretenimiento',
        'esportes': 'Deportes',
        'notícias': 'Noticias',
        'noticias': 'Noticias',
        'filmes': 'Películas',
        'infantil': 'Infantil',
        'documentários': 'Documentales',
        'documentarios': 'Documentales',
        'música': 'Música',
        'musica': 'Música',
        'variedades': 'Variedades',
        'religiosos': 'Religiosos',
        'adulto': 'Adultos',
        'educativo': 'Educativo',
        'globo': 'Brasil',
        'sbt': 'Brasil',
        'record': 'Brasil',
        'band': 'Brasil',
    }
    
    if not category_pt:
        return 'General'
    
    category_lower = category_pt.lower().strip()
    return category_map.get(category_lower, category_pt.capitalize())


def fetch_channels_from_api():
    """Obtiene los canales desde la API"""
    print(f"Obteniendo canales desde {API_URL}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://reidoscanais.io/'
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success') and 'data' in data:
            channels = data['data']
            print(f"Obtenidos {len(channels)} canales de la API")
            return channels
        else:
            print(f"Respuesta inesperada de la API: {data}")
            return []
            
    except requests.RequestException as e:
        print(f"Error al obtener canales de la API: {e}")
        return []


def update_channels_json(api_channels):
    """Actualiza el archivo canales.json con los canales de la API"""
    existing_channels = load_existing_channels()
    existing_ids = {ch.get('id', '') for ch in existing_channels}
    
    channels_added = 0
    channels_updated = 0
    channels_skipped = 0
    
    for api_channel in api_channels:
        # Extraer datos de la API
        slug = api_channel.get('id', '')
        name = api_channel.get('name', '')
        logo_url = api_channel.get('logo_url', '')
        embed_url = api_channel.get('embed_url', '')
        category = api_channel.get('category', '')
        is_active = api_channel.get('is_active', True)
        
        if not name or not embed_url:
            continue
        
        # Solo procesar canales activos
        if not is_active:
            channels_skipped += 1
            continue
        
        # Buscar si ya existe
        idx, existing = find_existing_channel(existing_channels, name, slug)
        
        if existing:
            # Agregar la URL como servidor adicional
            if add_url_to_channel(existing, embed_url):
                print(f"  Actualizado: {name} - agregado servidor {embed_url}")
                channels_updated += 1
            else:
                channels_skipped += 1
        else:
            # Crear nuevo canal
            mapped_category = map_category(category)
            new_id = generate_id(name, mapped_category, existing_ids)
            existing_ids.add(new_id)
            
            new_channel = {
                "id": new_id,
                "name": name,
                "image": logo_url,
                "iframe_url": json.dumps([embed_url]),
                "category": mapped_category,
                "country": "Brasil",
                "quality": "HD",
                "is_active": True
            }
            
            existing_channels.append(new_channel)
            channels_added += 1
            print(f"  Agregado: {name} ({new_id})")
    
    # Guardar cambios
    save_channels(existing_channels)
    
    print(f"\nResumen:")
    print(f"  Canales nuevos agregados: {channels_added}")
    print(f"  Canales actualizados: {channels_updated}")
    print(f"  Canales sin cambios/inactivos: {channels_skipped}")
    print(f"  Total de canales en archivo: {len(existing_channels)}")


def main():
    """Función principal"""
    print("=" * 60)
    print("Scraper de Rei dos Canais")
    print("=" * 60)
    
    # Obtener canales de la API
    api_channels = fetch_channels_from_api()
    
    if not api_channels:
        print("No se encontraron canales para procesar")
        return
    
    # Actualizar JSON
    print("\nActualizando canales.json...")
    update_channels_json(api_channels)
    
    print("\n¡Proceso completado!")


if __name__ == "__main__":
    main()
