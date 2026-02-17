import requests
import re

# Obtener URL fresca de deepcathink
deep_url = 'https://deepcathink.com/deportivo.php?player=desktop&live=espn1hd'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://elcanaldeportivo.com/'
}

try:
    r = requests.get(deep_url, headers=headers, timeout=10)
    print("Deep response len:", len(r.text))
except Exception as e:
    print("Error getting deepcathink:", e)
    exit(1)

# Extraer URL del array de caracteres
char_array_match = re.search(r'return\s*\(\s*\[((?:"[^"]*",?\s*)+)\]\.join\(["\']["\']?\)', r.text)
if char_array_match:
    chars = re.findall(r'"([^"]*)"', char_array_match.group(1))
    m3u8_url = ''.join(chars).replace('\\/', '/')
    print('M3U8 URL:', m3u8_url)
    
    # Probar diferentes referers
    referers = [
        'https://deepcathink.com/',
        'https://elcanaldeportivo.com/',
        'https://sanwalyaarpya.com/',
        None
    ]
    
    for ref in referers:
        test_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        if ref:
            test_headers['Referer'] = ref
        try:
            r2 = requests.head(m3u8_url, headers=test_headers, timeout=3)
            print(f'Referer {ref}: Status {r2.status_code}')
        except Exception as e:
            print(f'Referer {ref}: Error {e}')
else:
    print("No match found")
