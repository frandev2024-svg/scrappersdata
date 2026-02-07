import json
import html as html_lib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "xnxx.json"
OUTPUT_JSON = BASE_DIR / "xnxx.json"
TIMEOUT_SEC = 20


def extract_m3u8_url(html: str) -> str:
    if not html:
        return ""
    match = re.search(r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*", html)
    if not match:
        match = re.search(
            r"[\"'](?:file|src)[\"']\s*:\s*[\"']([^\"']+\.m3u8[^\"']*)",
            html,
        )
    if not match:
        return ""
    url = match.group(1) if match.lastindex else match.group(0)
    url = html_lib.unescape(url)
    url = url.replace("\\/", "/").replace("\\u0026", "&").replace("\\u002F", "/")
    return url


def fetch_embed_m3u8(session: requests.Session, embed_url: str, referer: Optional[str]) -> str:
    if not embed_url:
        return ""
    headers: Dict[str, str] = {}
    if referer:
        headers["Referer"] = referer
        headers["Origin"] = "https://www.xnxx.es"
    response = session.get(embed_url, headers=headers or None, timeout=TIMEOUT_SEC)
    response.encoding = "utf-8"
    return extract_m3u8_url(response.text)


def load_items() -> List[Dict[str, Any]]:
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"No existe {INPUT_JSON}")
    with INPUT_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    raise ValueError("Formato de xnxx.json no soportado")


def main() -> None:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })

    items = load_items()
    updated = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        embed_url = item.get("embed_url", "") or ""
        if not embed_url:
            continue

        # The embed url is used directly here.
        m3u8_url = fetch_embed_m3u8(session, embed_url, referer=item.get("url"))
        if not m3u8_url:
            continue

        item["embed_url"] = m3u8_url
        item["m3u8_url"] = m3u8_url
        updated += 1

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Actualizados: {updated}")


if __name__ == "__main__":
    main()
