"""
Script para limpiar enlaces problemáticos en películas, series y anime
- Elimina servidores doodstream
- Cambia /d/ por /e/ en URLs de embed
"""

import json
import re
import os
from datetime import datetime

class MediaLinksCleanup:
    def __init__(self):
        self.movies_file = 'peliculas.json'
        self.series_file = 'series.json'
        self.anime_file = 'anime.json'
        
        self.stats = {
            'movies_doodstream_removed': 0,
            'movies_links_fixed': 0,
            'series_doodstream_removed': 0,
            'series_links_fixed': 0,
            'anime_links_fixed': 0
        }
    
    def fix_download_links(self, url):
        """Cambia /d/ por /e/ en URLs para embed"""
        if '/d/' in url:
            fixed_url = url.replace('/d/', '/e/')
            return fixed_url, True
        return url, False
    
    def process_movies(self):
        """Procesa y limpia el archivo de películas"""
        try:
            print("📽️ Procesando películas...")
            
            with open(self.movies_file, 'r', encoding='utf-8') as f:
                movies = json.load(f)
            
            print(f"Total de películas a procesar: {len(movies)}")
            
            for i, movie in enumerate(movies):
                if i % 100 == 0:
                    print(f"Progreso películas: {i}/{len(movies)}")
                
                if isinstance(movie, dict) and 'servers' in movie:
                    if isinstance(movie['servers'], list):
                        # Filtrar servidores que NO sean doodstream
                        original_count = len(movie['servers'])
                        filtered_servers = []
                        
                        for server in movie['servers']:
                            # Verificar que sea un diccionario válido
                            if isinstance(server, dict):
                                server_name = server.get('server', '').lower()
                                embed_url = server.get('embed_url', '').lower()
                                
                                # Verificar tanto el campo server como la URL
                                if 'doodstream' not in server_name and 'doodstream' not in embed_url:
                                    # Arreglar link /d/ -> /e/
                                    if 'embed_url' in server and isinstance(server['embed_url'], str):
                                        fixed_url, was_fixed = self.fix_download_links(server['embed_url'])
                                        if was_fixed:
                                            server['embed_url'] = fixed_url
                                            self.stats['movies_links_fixed'] += 1
                                    filtered_servers.append(server)
                        
                        # Contar eliminados
                        removed = original_count - len(filtered_servers)
                        self.stats['movies_doodstream_removed'] += removed
                        movie['servers'] = filtered_servers
            
            # Guardar backup y archivo limpio
            backup_name = f'{self.movies_file}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            os.rename(self.movies_file, backup_name)
            print(f"Backup creado: {backup_name}")
            
            with open(self.movies_file, 'w', encoding='utf-8') as f:
                json.dump(movies, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Películas procesadas!")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando películas: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_series(self):
        """Procesa y limpia el archivo de series"""
        try:
            print("📺 Procesando series...")
            
            with open(self.series_file, 'r', encoding='utf-8') as f:
                series = json.load(f)
            
            print(f"Total de series a procesar: {len(series)}")
            
            for i, serie in enumerate(series):
                if i % 50 == 0:
                    print(f"Progreso series: {i}/{len(series)}")
                
                # Procesar episodios
                if 'episodios' in serie:
                    for episode in serie['episodios']:
                        if 'servidores' in episode:
                            # Filtrar servidores que NO sean doodstream
                            original_count = len(episode['servidores'])
                            filtered_servers = []
                            
                            for servidor in episode['servidores']:
                                if isinstance(servidor, dict):
                                    server_name = servidor.get('server', '').lower()
                                    server_url = servidor.get('url', '').lower()
                                    
                                    # Verificar tanto el campo server como la URL
                                    if 'doodstream' not in server_name and 'doodstream' not in server_url:
                                        # Arreglar link /d/ -> /e/
                                        if 'url' in servidor:
                                            fixed_url, was_fixed = self.fix_download_links(servidor['url'])
                                            if was_fixed:
                                                servidor['url'] = fixed_url
                                                self.stats['series_links_fixed'] += 1
                                        filtered_servers.append(servidor)
                            
                            episode['servidores'] = filtered_servers
                            # Contar eliminados
                            removed = original_count - len(episode['servidores'])
            
            # Guardar backup y archivo limpio
            backup_name = f'{self.series_file}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            os.rename(self.series_file, backup_name)
            print(f"Backup creado: {backup_name}")
            
            with open(self.series_file, 'w', encoding='utf-8') as f:
                json.dump(series, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Series procesadas!")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando series: {e}")
            return False
    
    def process_anime(self):
        """Procesa y limpia el archivo de anime"""
        try:
            print("🎌 Procesando anime...")
            
            with open(self.anime_file, 'r', encoding='utf-8') as f:
                animes = json.load(f)
            
            print(f"Total de animes a procesar: {len(animes)}")
            
            for i, anime in enumerate(animes):
                if i % 50 == 0:
                    print(f"Progreso anime: {i}/{len(animes)}")
                
                # Procesar temporadas y episodios
                if isinstance(anime, dict) and 'seasons' in anime:
                    seasons = anime.get('seasons', [])
                    if isinstance(seasons, list):
                        for season in seasons:
                            if isinstance(season, dict) and 'episodes' in season:
                                episodes = season.get('episodes', [])
                                if isinstance(episodes, list):
                                    for episode in episodes:
                                        if isinstance(episode, dict) and 'links' in episode:
                                            links = episode.get('links', {})
                                            if isinstance(links, dict):
                                                # Arreglar todos los tipos de links
                                                for link_type, link_url in links.items():
                                                    if isinstance(link_url, str):
                                                        fixed_url, was_fixed = self.fix_download_links(link_url)
                                                        if was_fixed:
                                                            episode['links'][link_type] = fixed_url
                                                            self.stats['anime_links_fixed'] += 1
            
            # Guardar backup y archivo limpio
            backup_name = f'{self.anime_file}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            os.rename(self.anime_file, backup_name)
            print(f"Backup creado: {backup_name}")
            
            with open(self.anime_file, 'w', encoding='utf-8') as f:
                json.dump(animes, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Anime procesado!")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando anime: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_cleanup(self):
        """Ejecuta la limpieza completa"""
        print("🚀 INICIANDO LIMPIEZA DE ENLACES")
        print("=" * 50)
        
        start_time = datetime.now()
        
        # Verificar archivos
        files_to_check = [self.movies_file, self.series_file, self.anime_file]
        for file_path in files_to_check:
            if not os.path.exists(file_path):
                print(f"❌ Archivo no encontrado: {file_path}")
                return False
        
        # Procesar archivos
        success_movies = self.process_movies()
        success_series = self.process_series()
        success_anime = self.process_anime()
        
        # Mostrar estadísticas
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 50)
        print("📊 ESTADÍSTICAS DE LIMPIEZA")
        print("=" * 50)
        print(f"🎬 Películas:")
        print(f"   • Servidores doodstream eliminados: {self.stats['movies_doodstream_removed']}")
        print(f"   • Enlaces /d/ → /e/ arreglados: {self.stats['movies_links_fixed']}")
        print(f"📺 Series:")
        print(f"   • Servidores doodstream eliminados: {self.stats['series_doodstream_removed']}")
        print(f"   • Enlaces /d/ → /e/ arreglados: {self.stats['series_links_fixed']}")
        print(f"🎌 Anime:")
        print(f"   • Enlaces /d/ → /e/ arreglados: {self.stats['anime_links_fixed']}")
        print(f"\n⏱️ Duración total: {duration}")
        print("=" * 50)
        
        if success_movies and success_series and success_anime:
            print("🎉 ¡LIMPIEZA COMPLETADA EXITOSAMENTE!")
            print("\n📋 Resumen de cambios:")
            print("🗑️ Eliminados todos los servidores doodstream")
            print("🔧 Convertidos todos los enlaces /d/ a /e/ para embed")
            print("💾 Creados backups automáticos de seguridad")
            return True
        else:
            print("❌ Algunos procesos fallaron")
            return False

def main():
    """Función principal"""
    try:
        cleaner = MediaLinksCleanup()
        success = cleaner.run_cleanup()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
        return 1
    except Exception as e:
        print(f"Error fatal: {e}")
        return 1

if __name__ == "__main__":
    exit(main())