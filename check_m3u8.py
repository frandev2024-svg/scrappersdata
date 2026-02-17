import json

data = json.load(open('peliculas.json', 'r', encoding='utf-8'))
movie = [m for m in data if m.get('tmdb_id') == 458156][0]
servers_with_m3u8 = [s for s in movie['servers'] if s.get('m3u8_url')]
print(f"Servidores con m3u8: {len(servers_with_m3u8)}/{len(movie['servers'])}")
print()
for s in servers_with_m3u8[:5]:
    m3u8 = s.get('m3u8_url', '')[:70]
    print(f"  - {s['server']} ({s['language']}): {m3u8}...")
