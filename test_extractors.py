from scraper_embed_extractor import extract_from_embed
import json

urls = [
    'https://niramirus.com/e/dsizj3khgzft',
    'https://streamwish.to/e/j1drbbyijhgt',
    'https://callistanise.com/v/s4u2xg73ly8r',
    'https://waaw.to/f/EANLa7XvtFt2',
]

results = {}
for url in urls:
    host = url.split('/')[2]
    print(f'\nProcesando {host}...')
    try:
        result = extract_from_embed(url)
        results[host] = result
        if result.get('error'):
            print(f'  ERROR: {result["error"][:80]}')
        elif result.get('best_url'):
            print(f'  OK: {result["best_url"][:80]}...')
        else:
            print(f'  No se encontraron URLs')
    except Exception as e:
        print(f'  EXCEPTION: {e}')

# Guardar en JSON
with open('embed_links.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print('\n' + '='*60)
print('RESUMEN - Guardado en embed_links.json')
print('='*60)

for host, data in results.items():
    status = 'OK' if data.get('best_url') else 'FAIL'
    urls_count = len(data.get('video_urls', {}))
    print(f'{host}: {status} ({urls_count} URLs)')
    if data.get('best_url'):
        print(f'  -> {data["best_url"][:100]}')
