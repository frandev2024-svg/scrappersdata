"""
Script temporal para extraer m3u8 de las películas John Wick
"""

import json
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from scraper_embed_extractor import extract_from_embed

# Películas a procesar
movies = [
    {
        "tmdb_id": 458156,
        "title": "John Wick 3: Parabellum",
        "year": "2019",
        "servers": [
            {"server": "streamwish", "quality": "HD", "language": "LATINO", "embed_url": "https://streamwish.to/e/0u9qe3zt9o1h"},
            {"server": "filemoon", "quality": "HD", "language": "LATINO", "embed_url": "https://bysejikuar.com/e/ja4c6net9gxb"},
            {"server": "vidhide", "quality": "HD", "language": "LATINO", "embed_url": "https://filelions.to/v/0uwoy6vbrhkq"},
            {"server": "voesx", "quality": "HD", "language": "LATINO", "embed_url": "https://voe.sx/e/ge5qk4mjnyzv"},
            {"server": "streamtape", "quality": "HD", "language": "LATINO", "embed_url": "https://streamtape.com/e/Q32lMBZ21OU0zdX"},
            {"server": "netu", "quality": "HD", "language": "LATINO", "embed_url": "https://hqq.tv/e/ck0veTd2NER6UThDaFVyQ25JTmRVQT09"},
            {"server": "streamwish", "quality": "HD", "language": "ESPANOL", "embed_url": "https://streamwish.to/e/1vws5ixk5jnj"},
            {"server": "filemoon", "quality": "HD", "language": "ESPANOL", "embed_url": "https://bysejikuar.com/e/n2838l3shi8n"},
            {"server": "vidhide", "quality": "HD", "language": "ESPANOL", "embed_url": "https://vidhidepro.com/v/orxt20qfrv33"},
            {"server": "voesx", "quality": "HD", "language": "ESPANOL", "embed_url": "https://voe.sx/e/dgigziyutzky"},
            {"server": "netu", "quality": "HD", "language": "ESPANOL", "embed_url": "https://hqq.tv/e/LzNoSm1YNHgxWE53SHZWclBwSGJhUT09"},
            {"server": "filemoon", "quality": "HD", "language": "SUB", "embed_url": "https://bysejikuar.com/e/bwnrkz07r0wy"},
            {"server": "vidhide", "quality": "HD", "language": "SUB", "embed_url": "https://vidhidepro.com/v/tdk1jzwfgdvs"},
            {"server": "voesx", "quality": "HD", "language": "SUB", "embed_url": "https://voe.sx/e/uhyj9ochyywx"},
            {"server": "streamtape", "quality": "HD", "language": "SUB", "embed_url": "https://streamtape.com/e/Gvlp2DP1wKi1XMW"},
            {"server": "netu", "quality": "HD", "language": "SUB", "embed_url": "https://hqq.tv/e/TXppTXNlYlZseENMVjdHNEhPSXBBQT09"}
        ]
    },
    {
        "tmdb_id": 324552,
        "title": "John Wick 2: Un Nuevo Día para Matar",
        "year": "2017",
        "servers": [
            {"server": "streamwish", "quality": "HD", "language": "LATINO", "embed_url": "https://streamwish.to/e/50fcal32etq8"},
            {"server": "filemoon", "quality": "HD", "language": "LATINO", "embed_url": "https://bysejikuar.com/e/dhlar1inzc0z"},
            {"server": "voesx", "quality": "HD", "language": "LATINO", "embed_url": "https://voe.sx/e/jdhss7y9z8ha"},
            {"server": "streamtape", "quality": "HD", "language": "LATINO", "embed_url": "https://streamtape.com/e/drDvYMJ8YXUkxaZ"},
            {"server": "netu", "quality": "HD", "language": "LATINO", "embed_url": "https://hqq.tv/e/M05PbGc2Y2J6L0lPWVVpYmlwaGZSQT09"},
            {"server": "streamwish", "quality": "HD", "language": "ESPANOL", "embed_url": "https://streamwish.to/e/gzswsfl8v0h8"},
            {"server": "filemoon", "quality": "HD", "language": "ESPANOL", "embed_url": "https://bysejikuar.com/e/i0z77ee1vd0p"},
            {"server": "voesx", "quality": "HD", "language": "ESPANOL", "embed_url": "https://voe.sx/e/b8frg2lnbqqz"},
            {"server": "netu", "quality": "HD", "language": "ESPANOL", "embed_url": "https://hqq.tv/e/d1diTHJkUE9BKytzUGs5WS94QkJCUT09"},
            {"server": "streamwish", "quality": "HD", "language": "SUB", "embed_url": "https://streamwish.to/e/k3ijewmc8459"},
            {"server": "filemoon", "quality": "HD", "language": "SUB", "embed_url": "https://bysejikuar.com/e/axcoigvcs6r7"},
            {"server": "voesx", "quality": "HD", "language": "SUB", "embed_url": "https://voe.sx/e/ymvgfkccfmro"},
            {"server": "netu", "quality": "HD", "language": "SUB", "embed_url": "https://hqq.tv/e/bHk1bHY4OXFSZzNJaklqcm0yeStRQT09"}
        ]
    },
    {
        "tmdb_id": 603692,
        "title": "John Wick 4",
        "year": "2023",
        "servers": [
            {"server": "streamtape", "quality": "HD", "language": "LATINO", "embed_url": "https://streamtape.com/e/zlq2AyoZZlSYq9W"},
            {"server": "netu", "quality": "HD", "language": "LATINO", "embed_url": "https://waaw.to/f/Rzto8pPPTjJ9"},
            {"server": "streamtape", "quality": "HD", "language": "ESPANOL", "embed_url": "https://streamtape.com/e/qa0aA0M9oOfzzvr"},
            {"server": "streamtape", "quality": "HD", "language": "SUB", "embed_url": "https://streamtape.com/e/o9Be0zqdLxCJ6A1"}
        ]
    },
    {
        "tmdb_id": 291984,
        "title": "The Death and Life of John F. Donovan",
        "year": "2019",
        "servers": [
            {"server": "vidhide", "quality": "HD", "language": "LATINO", "embed_url": "https://filelions.to/v/91rc1fw285oa"},
            {"server": "voesx", "quality": "HD", "language": "LATINO", "embed_url": "https://voe.sx/e/xkv3kyeaolq6"},
            {"server": "netu", "quality": "HD", "language": "LATINO", "embed_url": "https://waaw.to/f/fCykYsQSMJhM"},
            {"server": "vidhide", "quality": "HD", "language": "SUB", "embed_url": "https://filelions.to/v/r5iaeqwp8xlb"},
            {"server": "voesx", "quality": "HD", "language": "SUB", "embed_url": "https://voe.sx/e/7achmoc6aesy"},
            {"server": "netu", "quality": "HD", "language": "SUB", "embed_url": "https://waaw.to/f/83VH9V9QAbjR"}
        ]
    }
]

def main():
    successful = 0
    failed = 0
    skipped = 0
    
    for movie in movies:
        print(f"\n{'='*70}")
        print(f"🎬 {movie['title']} ({movie['year']}) - TMDB: {movie['tmdb_id']}")
        print(f"{'='*70}")
        
        for server in movie['servers']:
            embed_url = server.get('embed_url', '').strip()
            server_name = server.get('server', 'unknown')
            lang = server.get('language', '?')
            
            if not embed_url:
                print(f"  ⚠️ [{server_name}][{lang}] Sin URL de embed")
                skipped += 1
                continue
                
            print(f"\n  🔍 [{server_name}][{lang}] {embed_url}")
            
            try:
                result = extract_from_embed(embed_url)
                
                if result.get('best_url'):
                    server['m3u8_url'] = result['best_url']
                    print(f"     ✅ {result['best_url'][:80]}...")
                    successful += 1
                else:
                    error = result.get('error', 'No se encontró URL')
                    server['m3u8_url'] = None
                    server['m3u8_error'] = error
                    print(f"     ❌ Error: {error}")
                    failed += 1
                    
            except Exception as e:
                server['m3u8_url'] = None
                server['m3u8_error'] = str(e)
                print(f"     ❌ Excepción: {str(e)}")
                failed += 1
            
            time.sleep(0.5)  # Pausa entre requests
    
    print(f"\n{'='*70}")
    print(f"RESUMEN")
    print(f"{'='*70}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    print(f"⚠️ Omitidos: {skipped}")
    
    # Guardar resultado
    output_file = 'test_movies_m3u8_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Resultados guardados en: {output_file}")

if __name__ == '__main__':
    main()
