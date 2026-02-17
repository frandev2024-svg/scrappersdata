"""
Scraper para extraer URLs de video (m3u8, mp4, hls) de embeds como niramirus.com, streamwish, etc.
"""

import re
import requests
import json
import urllib3
from urllib.parse import urljoin, urlparse

# Desactivar warnings de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Headers para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

# Dominios alternativos que redirigen al contenido real
STREAMWISH_DOMAINS = [
    'streamwish.to', 'streamwish.com', 'awish.pro', 'dwish.pro',
    'ewish.pro', 'swish.pro', 'wishfast.top', 'fwish.to',
    'wish4u.net', 'kswplayer.info'
]
STREAMWISH_REAL_DOMAIN = 'sfastwish.com'  # Dominio que devuelve el HTML real

# Hosts de vidhide (usan el mismo packer que niramirus)
VIDHIDE_DOMAINS = [
    'vidhide.com', 'vidhidepro.com', 'vidhidevip.com',
    'callistanise.com', 'vidembed.me', 'vid2faf.site'
]

# Hosts de VOE (requieren tratamiento especial)
VOE_DOMAINS = [
    'voe.sx', 'voeunblock.com', 'voeunbl0ck.com',
    'voe-unblock.com', 'voeunblock1.com', 'voeunblock2.com',
    'voeunblock3.com', 'voeun-block.net', 'un-block-voe.net',
    'audaciousdefaulthouse.com', 'laaborede.com', 'yokeagogede.com',
    'lauradaydo.com', 'greensayconsci.com', 'madoffmede.com'
]

# Hosts de waaw.to
WAAW_DOMAINS = ['waaw.to', 'netu.tv', 'hqq.tv', 'hqq.to']


def unpack_js(packed_code: str) -> str:
    """
    Desempaqueta código JavaScript ofuscado con el típico packer p,a,c,k,e,d
    """
    # Extraer los parámetros del packer
    patterns = [
        r"eval\(function\(p,a,c,k,e,d\)\{.*?\}return p\}\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)\)\)",
        r"eval\(function\(p,a,c,k,e,d\)\{.*?\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)\)\)",
    ]
    
    match = None
    for pattern in patterns:
        match = re.search(pattern, packed_code, re.DOTALL)
        if match:
            break
    
    if not match:
        return None
    
    p, a, c, k = match.groups()
    a = int(a)
    c = int(c)
    k = k.split('|')
    
    # Función para convertir número a base (estilo JavaScript)
    def base_encode(num, base):
        """Convierte un número a la representación en una base dada (como JavaScript toString(base))"""
        if num == 0:
            return '0'
        
        digits = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        result = ''
        
        while num > 0:
            result = digits[num % base] + result
            num //= base
        
        return result if result else '0'
    
    # Crear el diccionario de reemplazo
    d = {}
    for i in range(c):
        key = base_encode(i, a)
        d[key] = k[i] if k[i] else key
    
    # Reemplazar en el código (usando word boundaries)
    def replacer(match):
        word = match.group(0)
        return d.get(word, word)
    
    unpacked = re.sub(r'\b(\w+)\b', replacer, p)
    return unpacked


def extract_video_urls(unpacked_js: str) -> dict:
    """
    Extrae las URLs de video m3u8 del código JavaScript desempaquetado
    """
    urls = {}
    
    # Buscar el objeto links o n que contiene las URLs
    # Formato: var links={"hls3":"url","hls4":"url","hls2":"url"}
    links_pattern = r'(?:links|n)\s*=\s*\{([^}]+)\}'
    links_match = re.search(links_pattern, unpacked_js)
    
    if links_match:
        links_content = links_match.group(1)
        # Extraer cada URL: "key":"value" - solo m3u8
        url_pairs = re.findall(r'"(\w+)"\s*:\s*"([^"]+)"', links_content)
        for key, value in url_pairs:
            if value and '.m3u8' in value and (value.startswith('http') or value.startswith('/')):
                urls[key] = value
    
    # Si no encontramos con el patrón anterior, buscar URLs m3u8 directamente
    if not urls:
        # Buscar m3u8 absolutas
        m3u8_matches = re.findall(r'(?:"|\')\s*(https?://[^\s"\']+\.m3u8[^\s"\']*)\s*(?:"|\')', unpacked_js)
        for i, match in enumerate(m3u8_matches):
            urls[f'm3u8_{i+1}'] = match
        
        # Buscar m3u8 relativas
        m3u8_rel = re.findall(r'(?:"|\')\s*(/[^\s"\']+\.m3u8[^\s"\']*)\s*(?:"|\')', unpacked_js)
        for i, match in enumerate(m3u8_rel):
            urls[f'm3u8_rel_{i+1}'] = match
    
    return urls


def extract_from_niramirus(embed_url: str, original_url: str = None) -> dict:
    """
    Extrae las URLs de video de un embed (niramirus, streamwish, etc.)
    """
    result = {
        'url': original_url or embed_url,
        'video_urls': {},
        'thumbnail': None,
        'title': None,
        'error': None
    }
    
    try:
        response = requests.get(embed_url, headers=HEADERS, timeout=30, verify=False)
        response.raise_for_status()
        html = response.text
        
        # Extraer título
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            result['title'] = title_match.group(1)
        
        # Extraer thumbnail
        thumb_match = re.search(r'<img\s+src="([^"]+_xt\.jpg)"', html)
        if thumb_match:
            result['thumbnail'] = thumb_match.group(1)
        
        # Buscar el código JavaScript ofuscado
        packed_match = re.search(r"(eval\(function\(p,a,c,k,e,d\)\{.*?\.split\('\|'\)\)\))", html, re.DOTALL)
        
        if not packed_match:
            result['error'] = 'No se encontró código JavaScript ofuscado'
            return result
        
        packed_code = packed_match.group(1)
        
        # Desempaquetar
        unpacked = unpack_js(packed_code)
        
        if not unpacked:
            result['error'] = 'No se pudo desempaquetar el código JavaScript'
            return result
        
        # Extraer URLs
        urls = extract_video_urls(unpacked)
        
        # Completar URLs relativas con el dominio base
        base_url = '/'.join(embed_url.split('/')[:3])
        for key, value in urls.items():
            if value.startswith('/'):
                urls[key] = base_url + value
        
        result['video_urls'] = urls
        
        # Si encontramos URLs, marcar la mejor opción (prioridad: hls4 > m3u8)
        if urls:
            # hls4 es el que funciona mejor (URL directa de niramirus con m3u8)
            priority_order = ['hls4', 'm3u8_1', 'hls2', 'hls3', 'mp4_1']
            for key in priority_order:
                if key in urls and '.m3u8' in urls[key]:
                    result['best_url'] = urls[key]
                    result['best_format'] = key
                    break
            
            # Si no encontramos ninguno de los prioritarios, usar el primero que sea m3u8
            if 'best_url' not in result:
                for key, url in urls.items():
                    if '.m3u8' in url:
                        result['best_url'] = url
                        result['best_format'] = key
                        break
        
    except requests.RequestException as e:
        result['error'] = f'Error de conexión: {str(e)}'
    except Exception as e:
        result['error'] = f'Error: {str(e)}'
    
    return result


def extract_video_url(embed_url: str) -> str:
    """
    Función simplificada que devuelve solo la mejor URL de video
    """
    result = extract_from_embed(embed_url)
    return result.get('best_url')


# Soporte para otros hosts de embed conocidos
def detect_host(embed_url: str) -> str:
    """
    Detecta el tipo de host del embed
    """
    url_lower = embed_url.lower()
    
    # Detectar niramirus
    if 'niramirus.com' in url_lower:
        return 'niramirus'
    
    # Detectar cualquier variante de streamwish
    for domain in STREAMWISH_DOMAINS:
        if domain in url_lower:
            return 'streamwish'
    if 'sfastwish.com' in url_lower or 'flaswish.com' in url_lower:
        return 'streamwish'
    
    # Detectar vidhide
    for domain in VIDHIDE_DOMAINS:
        if domain in url_lower:
            return 'vidhide'
    
    # Detectar VOE
    for domain in VOE_DOMAINS:
        if domain in url_lower:
            return 'voe'
    
    # Detectar waaw.to
    for domain in WAAW_DOMAINS:
        if domain in url_lower:
            return 'waaw'
    
    if 'filemoon' in url_lower:
        return 'filemoon'
    if 'doodstream' in url_lower:
        return 'doodstream'
    
    return 'unknown'


def normalize_streamwish_url(embed_url: str) -> str:
    """
    Convierte URLs de streamwish a sfastwish.com para obtener el HTML real
    """
    parsed = urlparse(embed_url)
    # Extraer el código del video (ej: j1drbbyijhgt)
    path = parsed.path
    if '/e/' in path:
        video_code = path.split('/e/')[-1].strip('/')
        return f'https://{STREAMWISH_REAL_DOMAIN}/e/{video_code}'
    return embed_url


def extract_from_waaw(embed_url: str) -> dict:
    """
    Extrae las URLs de video de waaw.to/netu.tv (tienen m3u8 directo en HTML)
    """
    result = {
        'url': embed_url,
        'video_urls': {},
        'thumbnail': None,
        'title': None,
        'error': None
    }
    
    try:
        # waaw.to usa /e/ para embed, /f/ para full page
        parsed = urlparse(embed_url)
        path = parsed.path
        
        # Convertir /f/ a /e/ si es necesario
        if '/f/' in path:
            video_code = path.split('/f/')[-1].strip('/')
            embed_url = f'https://waaw.to/e/{video_code}'
        
        response = requests.get(embed_url, headers=HEADERS, timeout=30, verify=False)
        response.raise_for_status()
        html = response.text
        
        # Extraer título
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            result['title'] = title_match.group(1)
        
        # Extraer thumbnail
        thumb_match = re.search(r'thumbnailUrl["\s]*content="([^"]+)"', html)
        if thumb_match:
            result['thumbnail'] = thumb_match.group(1)
        
        # Buscar m3u8 directo en el HTML
        m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        
        for i, url in enumerate(m3u8_matches):
            # Limpiar la URL
            url = url.replace('\\/', '/').strip()
            if url.endswith('.m3u8') or '.m3u8?' in url:
                result['video_urls'][f'm3u8_{i+1}'] = url
        
        # Si encontramos URLs, marcar la mejor
        if result['video_urls']:
            first_key = list(result['video_urls'].keys())[0]
            result['best_url'] = result['video_urls'][first_key]
            result['best_format'] = first_key
            
    except requests.RequestException as e:
        result['error'] = f'Error de conexión: {str(e)}'
    except Exception as e:
        result['error'] = f'Error: {str(e)}'
    
    return result


def extract_from_voe(embed_url: str) -> dict:
    """
    Extrae las URLs de video de VOE (voe.sx, lauradaydo.com, etc.)
    VOE usa un sistema de encoding complejo
    """
    result = {
        'url': embed_url,
        'video_urls': {},
        'thumbnail': None,
        'title': None,
        'error': None
    }
    
    try:
        # VOE puede redirigir a otro dominio
        response = requests.get(embed_url, headers=HEADERS, timeout=30, allow_redirects=True, verify=False)
        response.raise_for_status()
        html = response.text
        
        # Si hay redirección en JS, seguirla
        redirect_match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", html)
        if redirect_match and 'voe' not in redirect_match.group(1):
            redirect_url = redirect_match.group(1)
            response = requests.get(redirect_url, headers=HEADERS, timeout=30, verify=False)
            html = response.text
        
        # Extraer título
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            result['title'] = title_match.group(1)
        
        # Extraer thumbnail
        thumb_match = re.search(r'og:image["\s]*content="([^"]+)"', html)
        if thumb_match:
            result['thumbnail'] = thumb_match.group(1)
        
        # VOE tiene diferentes formatos de encoding
        # Formato 1: Buscar mp4 directo
        mp4_match = re.search(r"['\"]?(https?://[^'\"\\s]+\.mp4)['\"]?", html)
        if mp4_match and 'test-videos' not in mp4_match.group(1):
            result['video_urls']['mp4'] = mp4_match.group(1)
        
        # Formato 2: Buscar m3u8 directo
        m3u8_matches = re.findall(r'(https?://[^\s"\'\\]+\.m3u8[^\s"\'\\]*)', html)
        for i, url in enumerate(m3u8_matches):
            result['video_urls'][f'm3u8_{i+1}'] = url
        
        # Formato 3: Buscar en script con encoding base64/custom
        # VOE usa un encoding custom que parece base64 modificado
        # Buscar patron 'prompt' o similar que contenga la URL
        prompt_match = re.search(r"prompt\s*\(\s*['\"]([^'\"]+)['\"]", html)
        if prompt_match:
            result['video_urls']['prompt'] = prompt_match.group(1)
        
        # Buscar URLs de HLS en formato codificado
        hls_pattern = re.search(r'["\']hls["\']\s*:\s*["\']([^"\']+)["\']', html)
        if hls_pattern:
            result['video_urls']['hls'] = hls_pattern.group(1)
        
        # Si encontramos URLs, marcar la mejor
        if result['video_urls']:
            # Priorizar m3u8
            for key in result['video_urls']:
                if 'm3u8' in key:
                    result['best_url'] = result['video_urls'][key]
                    result['best_format'] = key
                    break
            else:
                first_key = list(result['video_urls'].keys())[0]
                result['best_url'] = result['video_urls'][first_key]
                result['best_format'] = first_key
        else:
            result['error'] = 'VOE requiere JavaScript para decodificar - no se encontraron URLs directas'
            
    except requests.RequestException as e:
        result['error'] = f'Error de conexión: {str(e)}'
    except Exception as e:
        result['error'] = f'Error: {str(e)}'
    
    return result


def extract_from_embed(embed_url: str) -> dict:
    """
    Función principal que detecta el host y extrae la URL apropiadamente
    """
    host = detect_host(embed_url)
    
    if host == 'streamwish':
        # Convertir a sfastwish.com para obtener el HTML real
        real_url = normalize_streamwish_url(embed_url)
        return extract_from_niramirus(real_url, original_url=embed_url)
    elif host == 'waaw':
        return extract_from_waaw(embed_url)
    elif host == 'voe':
        return extract_from_voe(embed_url)
    elif host in ('niramirus', 'vidhide', 'filemoon', 'unknown'):
        # Estos hosts usan el mismo método de packer
        return extract_from_niramirus(embed_url)
    else:
        # Intentar con el método genérico
        return extract_from_niramirus(embed_url)


# ============== MAIN ==============
if __name__ == '__main__':
    import sys
    
    # URL de prueba o desde argumentos
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = 'https://niramirus.com/e/dsizj3khgzft'
    
    print(f"\n{'='*60}")
    print(f"Extrayendo video de: {test_url}")
    print(f"{'='*60}\n")
    
    result = extract_from_embed(test_url)
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"📹 Título: {result.get('title', 'N/A')}")
        print(f"🖼️  Thumbnail: {result.get('thumbnail', 'N/A')}")
        print(f"\n📂 URLs encontradas:")
        for key, url in result.get('video_urls', {}).items():
            print(f"   [{key}]: {url}")
        
        if result.get('best_url'):
            print(f"\n✅ Mejor URL ({result.get('best_format')}):")
            print(f"   {result['best_url']}")
    
    print(f"\n{'='*60}")
    
    # También imprimir el resultado completo en JSON
    print("\n📋 Resultado completo (JSON):")
    print(json.dumps(result, indent=2, ensure_ascii=False))
