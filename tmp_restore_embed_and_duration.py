import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "xnxx.json"
OUTPUT_JSON = BASE_DIR / "xnxx.json"
TIMEOUT_SEC = 20
REQUEST_DELAY_SEC = 0.5


def parse_duration(text: str) -> Tuple[str, Optional[int]]:
    if not text:
        return "", None

    match_hours = re.search(r"(\d+)\s*h", text)
    match_minutes = re.search(r"(\d+)\s*min", text)
    match_seconds = re.search(r"(\d+)\s*sec", text)

    hours = int(match_hours.group(1)) if match_hours else 0
    minutes = int(match_minutes.group(1)) if match_minutes else 0
    seconds = int(match_seconds.group(1)) if match_seconds else 0

    total_seconds = hours * 3600 + minutes * 60 + seconds
    if total_seconds == 0:
        return "", None

    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}min")
    if seconds and not parts:
        parts.append(f"{seconds}sec")

    return " ".join(parts), total_seconds


def parse_embed_url(html: str) -> str:
    match = re.search(r"id=\"copy-video-embed\"[^>]*value=\"([^\"]+)\"", html)
    if match:
        value = match.group(1)
        src_match = re.search(r"src=\\\"([^\\\"]+)\\\"", value)
        if src_match:
            return src_match.group(1)

    match = re.search(r"https?://www\.xnxx\.es/embedframe/[a-z0-9]+", html)
    if match:
        return match.group(0)

    return ""


def fetch_embed_from_video(session: requests.Session, video_url: str) -> str:
    response = session.get(video_url, timeout=TIMEOUT_SEC)
    response.encoding = "utf-8"
    return parse_embed_url(response.text)


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

        meta = item.get("meta", "") or ""
        duration_text, duration_seconds = parse_duration(meta)
        if duration_text:
            item["duration_text"] = duration_text
        if duration_seconds:
            item["duration_seconds"] = duration_seconds

        embed_url = item.get("embed_url", "") or ""
        if ".m3u8" in embed_url:
            video_url = item.get("url", "") or ""
            if video_url:
                new_embed = fetch_embed_from_video(session, video_url)
                if new_embed:
                    item["embed_url"] = new_embed
                    updated += 1
                time.sleep(REQUEST_DELAY_SEC)

        if "m3u8_url" in item:
            item.pop("m3u8_url", None)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Actualizados: {updated}")


if __name__ == "__main__":
    main()
