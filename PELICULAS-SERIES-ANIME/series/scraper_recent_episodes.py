"""
Scraper de episodios recientes desde poseidonhd2.co/episodios
Extrae episodios nuevos y sus series asociadas
Guarda estructura: {episodios: [...], series_nuevas: [...]}
"""

import json
import time
import logging
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import os
import sys
import subprocess
from datetime import datetime
import re

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración
POSEIDON_BASE_URL = "https://www.poseidonhd2.co"
RECENT_EPISODES_URL = f"{POSEIDON_BASE_URL}/episodios"

class RecentEpisodesScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.recent_episodes = []
        self.new_series = []
        self.processed_episode_ids = set()
        
    def _get_next_data(self, html_text: str) -> Optional[Dict]:
        """Extrae el JSON de __NEXT_DATA__"""
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                content = script.string if script.string else script.get_text(strip=False)
                if content:
                    return json.loads(content)
        except Exception as e:
            logger.debug(f"Error parseando __NEXT_DATA__: {e}")
        return None

    def _find_dict_with_keys(self, data, required_keys: List[str]) -> Optional[Dict]:
        """Busca recursivamente un dict que contenga todas las keys requeridas"""
        if isinstance(data, dict):
            if all(k in data for k in required_keys):
                return data
            for value in data.values():
                found = self._find_dict_with_keys(value, required_keys)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_dict_with_keys(item, required_keys)
                if found:
                    return found
        return None

    def _find_videos_obj(self, data) -> Optional[Dict]:
        """Busca recursivamente un objeto con key 'videos'"""
        if isinstance(data, dict):
            if 'videos' in data and isinstance(data.get('videos'), dict):
                return data.get('videos')
            for value in data.values():
                found = self._find_videos_obj(value)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_videos_obj(item)
                if found:
                    return found
        return None

    def extraer_episodios_recientes(self, page_url: str = RECENT_EPISODES_URL) -> List[Dict]:
        """Extrae lista de episodios recientes desde la página"""
        episodios_urls = []
        
        try:
            response = self.session.get(page_url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar sección de episodios
            episodes_section = soup.find('div', class_='episodes')
            if not episodes_section:
                logger.warning("No se encontró div.episodes")
                return episodios_urls
            
            # Buscar lista de episodios
            episodes_list = episodes_section.find('ul', class_='MovieList')
            if not episodes_list:
                logger.warning("No se encontró ul.MovieList en episodes")
                return episodios_urls
            
            # Extraer items
            episode_items = episodes_list.find_all('li', class_='TPostMv')
            logger.info(f"Se encontraron {len(episode_items)} episodios recientes")
            
            for item in episode_items:
                try:
                    link_elem = item.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href')
                        if href:
                            full_url = urljoin(POSEIDON_BASE_URL, href)
                            
                            # Obtener número del episodio (ej: 3x2)
                            year_span = item.find('span', class_='Year')
                            ep_number = year_span.get_text(strip=True) if year_span else 'Unknown'
                            
                            # Obtener título
                            title_elem = item.find('h2', class_='Title')
                            title = title_elem.get_text(strip=True) if title_elem else ep_number
                            
                            episodios_urls.append({
                                'url': full_url,
                                'title': title,
                                'number': ep_number
                            })
                except Exception as e:
                    logger.debug(f"Error extrayendo episodio: {e}")
                    continue
            
            logger.info(f"Extraídas {len(episodios_urls)} URLs de episodios")
            
        except Exception as e:
            logger.error(f"Error extrayendo episodios recientes de {page_url}: {e}")
        
        return episodios_urls

    def extraer_verdadero_iframe(self, player_url: str) -> Optional[str]:
        """Extrae el verdadero iframe desde la URL del player"""
        try:
            response = self.session.get(player_url, timeout=10)
            response.encoding = 'utf-8'
            
            # Buscar el script con la URL del iframe
            pattern = r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]"
            match = re.search(pattern, response.text)
            
            if match:
                return match.group(1)
            
            logger.debug(f"No se encontró URL en player: {player_url}")
            
        except Exception as e:
            logger.debug(f"Error extrayendo iframe de {player_url}: {e}")
        
        return None

    def extraer_servidores_episodio(self, episodio_url: str) -> Dict:
        """Extrae servidores de un episodio"""
        servers_data = {
            'latino': [],
            'english': [],
            'spanish': [],
            'subtitulado': []
        }
        
        try:
            response = self.session.get(episodio_url, timeout=15)
            response.encoding = 'utf-8'
            
            # Obtener __NEXT_DATA__
            next_data = self._get_next_data(response.text)
            videos_obj = None
            if next_data:
                videos_obj = self._find_videos_obj(next_data)
            
            if videos_obj and isinstance(videos_obj, dict):
                for language, video_list in videos_obj.items():
                    if isinstance(video_list, list):
                        for video in video_list:
                            if isinstance(video, dict):
                                player_url = video.get('result', '')
                                # Extraer verdadero iframe del player
                                if 'player.php' in player_url:
                                    iframe_url = self.extraer_verdadero_iframe(player_url)
                                else:
                                    iframe_url = player_url
                                
                                server_info = {
                                    'url': iframe_url or player_url,
                                    'server': video.get('cyberlocker', ''),
                                    'quality': video.get('quality', 'HD'),
                                    'language': language
                                }
                                
                                if language in servers_data:
                                    servers_data[language].append(server_info)
                                else:
                                    if language not in servers_data:
                                        servers_data[language] = []
                                    servers_data[language].append(server_info)
                                
                                # Pequeña pausa
                                time.sleep(0.5)
            
            total_servers = sum(len(v) for v in servers_data.values())
            logger.info(f"Encontrados {total_servers} servidores")
            
        except Exception as e:
            logger.error(f"Error extrayendo servidores: {e}")
        
        return servers_data

    def extraer_info_episodio(self, episodio_url: str) -> Optional[Dict]:
        """Extrae información completa del episodio y su serie"""
        try:
            response = self.session.get(episodio_url, timeout=15)
            response.encoding = 'utf-8'
            
            next_data = self._get_next_data(response.text)
            if not next_data:
                logger.warning("No se encontró __NEXT_DATA__")
                return None
            
            # Extraer info del episodio
            props = next_data.get('props', {}).get('pageProps', {})
            episode_data = props.get('episode', {})
            serie_data = props.get('serie', {})
            
            if not episode_data or not serie_data:
                logger.warning("Faltan datos de episodio o serie")
                return None
            
            # Extraer servidores
            servers = self.extraer_servidores_episodio(episodio_url)
            
            # Construir estructura del episodio
            ep_info = {
                'tmdb_id': episode_data.get('TMDbId'),
                'serie_tmdb_id': serie_data.get('TMDbId'),
                'serie_title': serie_data.get('titles', {}).get('name', 'Unknown'),
                'title': episode_data.get('title'),
                'number_text': f"{props.get('season', {}).get('number', 0)}x{episode_data.get('number', 0)}",
                'season': props.get('season', {}).get('number', 0),
                'episode': episode_data.get('number', 0),
                'image': episode_data.get('image', ''),
                'servers': servers,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Si es una serie nueva, extraer información completa de la serie
            if serie_data.get('TMDbId') not in [s['tmdb_id'] for s in self.new_series]:
                serie_info = {
                    'tmdb_id': serie_data.get('TMDbId'),
                    'title': serie_data.get('titles', {}).get('name', 'Unknown'),
                    'year': serie_data.get('releaseDate', '').split('-')[0] if serie_data.get('releaseDate') else '',
                    'overview': serie_data.get('overview', '')[:200],
                    'rating': serie_data.get('rate', {}).get('average', 0),
                    'genres': [g.get('name', '') for g in serie_data.get('genres', [])],
                    'poster': serie_data.get('images', {}).get('poster', ''),
                    'backdrop': serie_data.get('images', {}).get('backdrop', '')
                }
                
                # Agregar un episodio de prueba con la estructura de temporadas
                season_num = props.get('season', {}).get('number', 1)
                serie_info['seasons'] = [{
                    'number': season_num,
                    'episodes': [{
                        'title': episode_data.get('title'),
                        'number_text': ep_info['number_text'],
                        'servers': servers
                    }]
                }]
                
                self.new_series.append(serie_info)
            
            return ep_info
            
        except Exception as e:
            logger.error(f"Error extrayendo info del episodio: {e}")
            return None

    def procesar_episodios_recientes(self, max_episodes: int = 20):
        """Procesa episodios recientes"""
        logger.info(f"Extrayendo episodios recientes desde {RECENT_EPISODES_URL}...")
        
        episodios_urls = self.extraer_episodios_recientes()
        
        for idx, ep_info in enumerate(episodios_urls[:max_episodes]):
            try:
                logger.info(f"\n--- Episodio {idx + 1}/{min(len(episodios_urls), max_episodes)} ---")
                logger.info(f"Procesando: {ep_info['title']}")
                
                # Extraer información completa
                full_info = self.extraer_info_episodio(ep_info['url'])
                if not full_info:
                    logger.warning(f"No se pudo obtener información de {ep_info['title']}")
                    continue
                
                # Evitar duplicados
                if full_info.get('tmdb_id') in self.processed_episode_ids:
                    logger.info(f"Episodio ya procesado: {full_info['title']}")
                    continue
                
                self.recent_episodes.append(full_info)
                self.processed_episode_ids.add(full_info.get('tmdb_id'))
                
                logger.info(f"✅ Episodio agregado: {full_info['title']}")
                
                # Pausa entre episodios
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error procesando episodio {ep_info.get('title')}: {e}")
                continue

    def guardar_episodios_recientes(self, output_file: str = 'episodios_recientes.json'):
        """Guarda episodios recientes en JSON"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, output_file)
            
            # Estructura de salida
            output_data = {
                'episodios_recientes': self.recent_episodes,
                'series_nuevas': self.new_series,
                'total_episodios': len(self.recent_episodes),
                'total_series_nuevas': len(self.new_series),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Guardados {len(self.recent_episodes)} episodios en {full_path}")
            logger.info(f"✅ Guardadas {len(self.new_series)} series nuevas")
            
        except Exception as e:
            logger.error(f"Error guardando episodios recientes: {e}")

    def actualizar_series_json(self, series_file: str = '../series.json'):
        """Actualiza el archivo series.json con nuevas series"""
        if not self.new_series:
            return
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, series_file)
            
            # Leer series existentes
            series_existentes = {}
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        series_existentes = {s['tmdb_id']: s for s in data}
                    except:
                        pass
            
            # Agregar nuevas series
            for serie in self.new_series:
                if serie['tmdb_id'] not in series_existentes:
                    series_existentes[serie['tmdb_id']] = serie
                    logger.info(f"✅ Serie nueva agregada a series.json: {serie['title']}")
            
            # Guardar
            series_finales = list(series_existentes.values())
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(series_finales, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Actualizados {len(series_finales)} registros en {full_path}")
            
        except Exception as e:
            logger.error(f"Error actualizando series.json: {e}")

    def run(self, max_episodes: int = 20):
        """Ejecuta el scraper"""
        logger.info("Iniciando scraper de episodios recientes...")
        
        try:
            self.procesar_episodios_recientes(max_episodes=max_episodes)
            self.guardar_episodios_recientes()
            self.actualizar_series_json()
            
            logger.info(f"\n✅ Scraping completado. Total: {len(self.recent_episodes)} episodios recientes")
            
        except KeyboardInterrupt:
            logger.info("Scraper interrumpido por el usuario")
        except Exception as e:
            logger.error(f"Error en el scraper: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scraper de episodios recientes desde poseidonhd2.co')
    parser.add_argument('--max-episodes', type=int, default=20, help='Número máximo de episodios a scrapear')
    
    args = parser.parse_args()
    
    scraper = RecentEpisodesScraper()
    scraper.run(max_episodes=args.max_episodes)


if __name__ == '__main__':
    main()
