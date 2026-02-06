"""
Script para eliminar solo el anime con el link específico
"""

import json
import os

def remove_anime_with_specific_link():
    """Elimina animes que contengan el link específico"""
    try:
        print("Cargando anime.json...")
        with open('anime.json', 'r', encoding='utf-8') as f:
            animes = json.load(f)
        
        print(f"Total de animes antes: {len(animes)}")
        
        target_link = "https://linkinpork.com?s=J6PP9PXiyII6ScAW.3BY6ymHj8dL-KlvR8HmOAYJ5gUEUXI0wJYwUdVCaLKWdKJZmesEENqv93BEO5b9Bwny10-XmVxHwCJuPnZqogXNhjuWTvRdQBZh3kNRfRV4ahwLNjWsN3JrV0eziKTCaHvW5CTXo3uZCr0m4Kg.MjFJLGOzvzjCuY8TeGMeHQ"
        
        filtered_animes = []
        removed_count = 0
        
        for anime in animes:
            anime_contains_link = False
            
            # Verificar que anime sea un diccionario
            if not isinstance(anime, dict):
                filtered_animes.append(anime)
                continue
            
            # Buscar el link en las temporadas y episodios
            seasons = anime.get('seasons', [])
            if seasons and isinstance(seasons, list):
                for season in seasons:
                    if not isinstance(season, dict):
                        continue
                    episodes = season.get('episodes', [])
                    if episodes and isinstance(episodes, list):
                        for episode in episodes:
                            if not isinstance(episode, dict):
                                continue
                            links = episode.get('links', {})
                            if isinstance(links, dict) and links.get('link-sub-mega') == target_link:
                                anime_contains_link = True
                                break
                    if anime_contains_link:
                        break
            
            if anime_contains_link:
                print(f"Eliminando anime: {anime.get('title', 'Sin título')} (ID: {anime.get('id')})")
                removed_count += 1
            else:
                filtered_animes.append(anime)
        
        print(f"Animes eliminados: {removed_count}")
        print(f"Total de animes después: {len(filtered_animes)}")
        
        # Backup
        print("Creando backup...")
        import shutil
        shutil.copy2('anime.json', 'anime_backup_before_removal.json')
        
        # Guardar archivo filtrado
        print("Guardando archivo filtrado...")
        with open('anime.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_animes, f, ensure_ascii=False, indent=2)
        
        print("✅ Animes eliminados exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error eliminando animes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    remove_anime_with_specific_link()