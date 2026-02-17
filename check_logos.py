import json

events = json.load(open('partidos.json', encoding='utf-8'))

# Eventos SIN liga pero con equipos
print("Eventos SIN liga (equipos sin identificar):")
sin_liga = [(e.get('equipos', ''), e.get('deporte', '')) for e in events if not e.get('liga')]
for eq, dep in sorted(set(sin_liga)):
    print(f"  - {eq} ({dep})")
