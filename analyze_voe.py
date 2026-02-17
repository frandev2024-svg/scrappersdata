import re

# VOE - buscar en el HTML
with open('debug_lauradaydo_com.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar variable source
source_match = re.search(r"var source='([^']+)'", content)
if source_match:
    print(f"source: {source_match.group(1)[:100]}")

# Buscar HLS 
hls = re.findall(r'https?://[^\s"\']+?\.m3u8[^\s"\']*', content)
print(f"HLS: {hls}")

# El JSON encoded
json_match = re.search(r'application/json">\["([^"]+)"\]', content)
if json_match:
    print(f"JSON encoded (first 200): {json_match.group(1)[:200]}")
