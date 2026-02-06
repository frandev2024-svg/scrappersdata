"""
Script para eliminar elementos específicos del JSON
"""

import json
import os

def remove_series_by_ids():
    """Elimina series específicas por ID"""
    try:
        print("Cargando series.json...")
        with open('series.json', 'r', encoding='utf-8') as f:
            series = json.load(f)
        
        print(f"Total de series antes: {len(series)}")
        
        # IDs a eliminar
        ids_to_remove = [1, 2, 3, 4]
        
        # Filtrar series que NO tengan esos IDs
        filtered_series = []
        removed_count = 0
        
        for serie in series:
            if serie.get('id') in ids_to_remove:
                print(f"Eliminando serie ID {serie.get('id')}: {serie.get('name', 'Sin nombre')}")
                removed_count += 1
            else:
                filtered_series.append(serie)
        
        print(f"Series eliminadas: {removed_count}")
        print(f"Total de series después: {len(filtered_series)}")
        
        # Backup
        print("Creando backup...")
        os.rename('series.json', 'series_backup_before_removal.json')
        
        # Guardar archivo filtrado
        print("Guardando archivo filtrado...")
        with open('series.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_series, f, ensure_ascii=False, indent=2)
        
        print("✅ Series eliminadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error eliminando series: {e}")
        return False

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
        os.rename('anime.json', 'anime_backup_before_removal.json')
        
        # Guardar archivo filtrado
        print("Guardando archivo filtrado...")
        with open('anime.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_animes, f, ensure_ascii=False, indent=2)
        
        print("✅ Animes eliminados exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error eliminando animes: {e}")
        return False

def main():
    print("=== ELIMINACIÓN DE ELEMENTOS ESPECÍFICOS ===")
    
    # Eliminar series
    print("\n1. Eliminando series específicas...")
    success_series = remove_series_by_ids()
    
    # Eliminar animes
    print("\n2. Eliminando animes con link específico...")
    success_anime = remove_anime_with_specific_link()
    
    # Resumen
    print("\n=== RESUMEN ===")
    print(f"Series: {'✅ Eliminadas' if success_series else '❌ Error'}")
    print(f"Animes: {'✅ Eliminados' if success_anime else '❌ Error'}")
    
    if success_series and success_anime:
        print("\n🎉 ¡Eliminación completada exitosamente!")
    else:
        print("\n⚠️  Algunos procesos fallaron. Revisa los backups.")

if __name__ == "__main__":
    main()