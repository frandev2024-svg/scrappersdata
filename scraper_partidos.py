import base64
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_JSON = BASE_DIR / "partidos.json"

# Configuración de GitHub
REPO_PATH = BASE_DIR / "PELICULAS-SERIES-ANIME" / "peliculas" / "scrappersdata"

ELCANALDEPORTIVO_URL = "https://elcanaldeportivo.com/partidos.json"
STREAMX10_URL = "https://streamx10.cloud/json/agenda345.json"
BOLALOCA_URL = "https://bolaloca.my/"
ANTENASPORT_URL = "https://antenasport.top/index2.txt"
PIRLOTV_URL = "https://pirlotvoficial.com/"
TVLIBREE_URL = "https://tvlibree.com/agenda/"
TVTVHD_URL = "https://tvtvhd.com/eventos/"

TIMEOUT_SEC = 20

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CH_NAME_MAP: Dict[int, str] = {
    1: "beIN 1",
    2: "beIN 2",
    3: "beIN 3",
    4: "beIN max 4",
    5: "beIN max 5",
    6: "beIN max 6",
    7: "beIN max 7",
    8: "beIN max 8",
    9: "beIN max 9",
    10: "beIN max 10",
    11: "canal+",
    12: "canal+ foot",
    13: "canal+ sport",
    14: "canal+ sport360",
    15: "eurosport1",
    16: "eurosport2",
    17: "rmc sport1",
    18: "rmc sport2",
    19: "equipe",
    20: "LIGUE 1 FR",
    21: "LIGUE 1 FR",
    22: "LIGUE 1 FR",
    23: "automoto",
    24: "tf1",
    25: "tmc",
    26: "m6",
    27: "w9",
    28: "france2",
    29: "france3",
    30: "france4",
    31: "C+Live 1",
    32: "C+Live 2",
    33: "C+Live 3",
    34: "C+Live 4",
    35: "C+Live 5",
    36: "C+Live 6",
    37: "C+Live 7",
    38: "C+Live 8",
    39: "C+Live 9",
    40: "C+Live 10",
    41: "C+Live 11",
    42: "C+Live 12",
    43: "C+Live 13",
    44: "C+Live 14",
    45: "C+Live 15",
    46: "C+Live 16",
    47: "C+Live 17",
    48: "C+Live 18",
    49: "ES m.laliga",
    50: "ES m.laliga2",
    51: "ES DAZN liga",
    52: "ES DAZN liga2",
    53: "ES LALIGA HYPERMOTION",
    54: "ES LALIGA HYPERMOTION2",
    55: "ES Vamos",
    56: "ES DAZN 1",
    57: "ES DAZN 2",
    58: "ES DAZN 3",
    59: "ES DAZN 4",
    60: "ES DAZN F1",
    61: "ES M+ Liga de Campeones",
    62: "ES M+ Deportes",
    63: "ES M+ Deportes2",
    64: "ES M+ Deportes3",
    65: "ES M+ Deportes4",
    66: "ES M+ Deportes5",
    67: "ES M+ Deportes6",
    68: "TUDN USA",
    69: "beIN En espanol",
    70: "FOX Deportes",
    71: "ESPN Deportes",
    72: "NBC UNIVERSO",
    73: "Telemundo",
    74: "GOL espanol",
    75: "TNT sport arg",
    76: "ESPN Premium",
    77: "TyC Sports",
    78: "FOXsport1 arg",
    79: "FOXsport2 arg",
    80: "FOXsport3 arg",
    81: "WINsport+",
    82: "WINsport",
    83: "TNTCHILE Premium",
    84: "Liga1MAX",
    85: "GOLPERU",
    86: "Zapping sports",
    87: "ESPN1",
    88: "ESPN2",
    89: "ESPN3",
    90: "ESPN4",
    91: "ESPN5",
    92: "ESPN6",
    93: "ESPN7",
    94: "directv",
    95: "directv2",
    96: "directv+",
    97: "ESPN1MX",
    98: "ESPN2MX",
    99: "ESPN3MX",
    100: "ESPN4MX",
    101: "FOXsport1MX",
    102: "FOXsport2MX",
    103: "FOXsport3MX",
    104: "FOX SPORTS PREMIUM",
    105: "TVC Deportes",
    106: "TUDNMX",
    107: "CANAL5",
    108: "Azteca 7",
    109: "VTV plus",
    110: "DE bundliga10",
    111: "DE bundliga1",
    112: "DE bundliga2",
    113: "DE bundliga3",
    114: "DE bundliga4",
    115: "DE bundliga5",
    116: "DE bundliga6",
    117: "DE bundliga7",
    118: "DE bundliga8",
    119: "DE bundliga9 (mix)",
    120: "DE skyde PL",
    121: "DE skyde f1",
    122: "DE skyde tennis",
    123: "DE dazn 1",
    124: "DE dazn 2",
    125: "DE Sportdigital Fussball",
    126: "UK TNT SPORT",
    127: "UK SKY MAIN",
    128: "UK SKY FOOT",
    129: "UK EPL 3PM",
    130: "UK EPL 3PM",
    131: "UK EPL 3PM",
    132: "UK EPL 3PM",
    133: "UK EPL 3PM",
    134: "UK F1",
    135: "UK SPFL",
    136: "UK SPFL",
    137: "IT DAZN",
    138: "IT SKYCALCIO",
    139: "IT FEED",
    140: "IT FEED",
    141: "NL ESPN 1",
    142: "NL ESPN 2",
    143: "NL ESPN 3",
    144: "PT SPORT 1",
    145: "PT SPORT 2",
    146: "PT SPORT 3",
    147: "PT BTV",
    148: "GR SPORT 1",
    149: "GR SPORT 2",
    150: "GR SPORT 3",
    151: "TR BeIN sport 1",
    152: "TR BeIN sport 2",
    153: "BE channel1",
    154: "BE channel2",
    155: "EXTRA SPORT1",
    156: "EXTRA SPORT2",
    157: "EXTRA SPORT3",
    158: "EXTRA SPORT4",
    159: "EXTRA SPORT5",
    160: "EXTRA SPORT6",
    161: "EXTRA SPORT7",
    162: "EXTRA SPORT8",
    163: "EXTRA SPORT9",
    164: "EXTRA SPORT10",
    165: "EXTRA SPORT11",
    166: "EXTRA SPORT12",
    167: "EXTRA SPORT13",
    168: "EXTRA SPORT14",
    169: "EXTRA SPORT15",
    170: "EXTRA SPORT16",
    171: "EXTRA SPORT17",
    172: "EXTRA SPORT18",
    173: "EXTRA SPORT19",
    174: "EXTRA SPORT20",
    175: "EXTRA SPORT21",
    176: "EXTRA SPORT22",
    177: "EXTRA SPORT23",
    178: "EXTRA SPORT24",
    179: "EXTRA SPORT25",
    180: "EXTRA SPORT26",
    181: "EXTRA SPORT27",
    182: "EXTRA SPORT28",
    183: "EXTRA SPORT30",
    184: "EXTRA SPORT31",
    185: "EXTRA SPORT32",
    186: "EXTRA SPORT33",
    187: "EXTRA SPORT34",
    188: "EXTRA SPORT35",
    189: "EXTRA SPORT36",
    190: "EXTRA SPORT37",
    191: "EXTRA SPORT38",
    192: "EXTRA SPORT39",
    193: "EXTRA SPORT40",
    194: "EXTRA SPORT41",
    195: "EXTRA SPORT42",
    196: "EXTRA SPORT43",
    197: "EXTRA SPORT44",
    198: "EXTRA SPORT45",
    199: "EXTRA SPORT46",
    200: "EXTRA SPORT47",
}


@dataclass
class SourceEvent:
    date_value: datetime
    date_offset: int


def today_arg_date() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=3)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def format_argentina(dt_arg: datetime) -> str:
    return dt_arg.strftime("%Y-%m-%d %H:%M")


def format_utc(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(
    dt_arg: datetime,
    logo: str,
    liga: str,
    equipos: str,
    canales: List[Dict[str, Any]],
    date_offset: int,
) -> Dict[str, Any]:
    dt_utc = dt_arg + timedelta(hours=3)
    return {
        "hora_utc": format_utc(dt_utc),
        "hora_argentina": format_argentina(dt_arg),
        "logo": logo or "",
        "liga": liga or "",
        "equipos": equipos or "",
        "canales": canales or [],
        "date_offset": date_offset,
    }


def make_abs_url(base: str, value: str) -> str:
    if not value:
        return ""
    return urljoin(base, value)


def extract_iframe_src(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        return iframe.get("src").strip()
    match = re.search(r"<iframe[^>]+src=['\"]([^'\"]+)['\"]", html_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def decode_base64(value: str) -> str:
    if not value:
        return ""
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.b64decode(padded).decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def find_date_in_text(text: str) -> Optional[datetime]:
    if not text:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d")
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        return datetime.strptime(match.group(0), "%d/%m/%Y")
    match = re.search(r"(\d{2})-(\d{2})-(\d{4})", text)
    if match:
        return datetime.strptime(match.group(0), "%d-%m-%Y")
    return None


def parse_league_and_teams(text: str) -> Tuple[str, str]:
    clean = normalize_ws(text)
    if ":" in clean:
        left, right = clean.split(":", 1)
        return left.strip(), right.strip()
    return "", clean


def channel_name_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    name = Path(parsed.path).stem
    name = name.replace("-", " ").replace("_", " ")
    return normalize_ws(name)


def filter_bad_tvlibree_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    if "la14hd.com" in lower:
        return False
    if "la12hd" in lower:
        return False
    return True


def extract_onclick_urls(html_text: str) -> List[str]:
    if not html_text:
        return []
    urls = re.findall(r"iframe'\)\.src='([^']+)'", html_text)
    if not urls:
        urls = re.findall(r"iframe\)\.src='([^']+)'", html_text)
    return [u.strip() for u in urls if u.strip()]


def fetch_html(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=TIMEOUT_SEC)
    response.encoding = "utf-8"
    return response.text


def parse_elcanaldeportivo(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        response = session.get(ELCANALDEPORTIVO_URL, timeout=TIMEOUT_SEC)
        response.encoding = "utf-8"
        data = response.json()
    except Exception as exc:
        logger.error("elcanaldeportivo error: %s", exc)
        return events

    for item in data if isinstance(data, list) else []:
        try:
            dt_utc = datetime.strptime(item.get("hora_utc", ""), "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            continue
        dt_arg = dt_utc - timedelta(hours=3)
        date_offset = (dt_arg.date() - dt_utc.date()).days
        logo = item.get("logo") or ""
        logo = make_abs_url("https://elcanaldeportivo.com/", logo)
        liga = (item.get("liga") or "").strip()
        if liga.endswith(":"):
            liga = liga[:-1].strip()
        equipos = item.get("equipos") or ""
        canales: List[Dict[str, Any]] = []
        for ch in item.get("canales") or []:
            ch_url = ch.get("url") or ""
            iframe_url = ""
            if ch_url:
                try:
                    html_text = fetch_html(session, ch_url)
                    iframe_url = extract_iframe_src(html_text)
                    iframe_url = make_abs_url(ch_url, iframe_url)
                except Exception:
                    iframe_url = ""
            canales.append({
                "nombre": ch.get("nombre") or "",
                "url": iframe_url or ch_url,
                "calidad": ch.get("calidad") or "",
            })
        events.append(build_event(dt_arg, logo, liga, equipos, canales, date_offset))
    return events


def parse_streamx10(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        response = session.get(STREAMX10_URL, timeout=TIMEOUT_SEC)
        response.encoding = "utf-8"
        data = response.json()
    except Exception as exc:
        logger.error("streamx10 error: %s", exc)
        return events

    for item in data if isinstance(data, list) else []:
        date_str = item.get("date") or ""
        time_str = item.get("time") or ""
        try:
            dt_source = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            continue
        dt_arg = dt_source + timedelta(hours=2)
        date_offset = (dt_arg.date() - dt_source.date()).days
        title = item.get("title") or ""
        liga, equipos = parse_league_and_teams(title)
        if not liga:
            liga = item.get("category") or ""
        link = item.get("link") or ""
        canales = [{"nombre": "StreamX10", "url": link, "calidad": ""}] if link else []
        events.append(build_event(dt_arg, "", liga, equipos, canales, date_offset))
    return events


def parse_bolaloca(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        html_text = fetch_html(session, BOLALOCA_URL)
    except Exception as exc:
        logger.error("bolaloca error: %s", exc)
        return events

    lines = [normalize_ws(line) for line in html_text.splitlines()]
    pattern = re.compile(
        r"^(\d{2}-\d{2}-\d{4})\s+\((\d{2}:\d{2})\)\s+(.+?)\s*:\s*(.+?)\s*(\(.+\))$"
    )

    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        date_str, time_str, liga, equipos, channels_raw = match.groups()
        try:
            dt_source = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
        except Exception:
            continue
        dt_arg = dt_source - timedelta(hours=4)
        date_offset = (dt_arg.date() - dt_source.date()).days
        channel_tokens = re.findall(r"CH(\d+)", channels_raw)
        canales: List[Dict[str, Any]] = []
        for token in channel_tokens:
            try:
                ch_num = int(token)
            except Exception:
                continue
            ch_name = CH_NAME_MAP.get(ch_num, f"CH{ch_num}")
            for source_name, player_id in ("WIGI", 1), ("HOCA", 2), ("CAST", 3):
                canales.append({
                    "nombre": f"{ch_name} ({source_name})",
                    "url": f"https://bolaloca.my/player/{player_id}/{ch_num}",
                    "calidad": "",
                })
        events.append(build_event(dt_arg, "", liga, equipos, canales, date_offset))
    return events


def parse_antenasport(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        text = fetch_html(session, ANTENASPORT_URL)
    except Exception as exc:
        logger.error("antenasport error: %s", exc)
        return events

    current_date: Optional[datetime] = None
    current_title: Optional[str] = None
    current_time: Optional[str] = None
    current_urls: List[str] = []

    def flush_current() -> None:
        nonlocal current_title, current_time, current_urls, current_date
        if not current_date or not current_title or not current_time:
            current_title = None
            current_time = None
            current_urls = []
            return
        try:
            dt_source = datetime.strptime(
                f"{current_date.strftime('%Y-%m-%d')} {current_time}", "%Y-%m-%d %H:%M"
            )
        except Exception:
            current_title = None
            current_time = None
            current_urls = []
            return
        dt_arg = dt_source - timedelta(hours=5)
        date_offset = (dt_arg.date() - dt_source.date()).days
        liga, equipos = parse_league_and_teams(current_title)
        canales = [
            {"nombre": channel_name_from_url(url), "url": url, "calidad": ""}
            for url in current_urls
        ]
        events.append(build_event(dt_arg, "", liga, equipos, canales, date_offset))
        current_title = None
        current_time = None
        current_urls = []

    for raw_line in text.splitlines():
        line = normalize_ws(raw_line)
        if not line:
            continue
        if re.match(r"^-{5,}$", line):
            flush_current()
            continue
        if re.match(r"^[A-Za-z]+,\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}$", line):
            try:
                current_date = datetime.strptime(line, "%A, %d %B %Y")
            except Exception:
                current_date = None
            continue
        if re.match(r"^\d{2}:\d{2}\s+", line):
            flush_current()
            parts = line.split(" ", 1)
            if len(parts) == 2:
                current_time = parts[0].strip()
                current_title = parts[1].strip()
            continue
        if line.startswith("http"):
            current_urls.append(line)

    flush_current()
    return events


def parse_pirlotvoficial(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        html_text = fetch_html(session, PIRLOTV_URL)
    except Exception as exc:
        logger.error("pirlotvoficial error: %s", exc)
        return events

    soup = BeautifulSoup(html_text, "html.parser")
    tbody = soup.find("tbody")
    if not tbody:
        return events

    base_date = today_arg_date().date()

    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        time_span = cols[0].find("span", class_="t")
        time_str = time_span.get_text(strip=True) if time_span else ""
        if not time_str:
            continue
        liga_text = normalize_ws(cols[2].get_text(" ", strip=True))
        match_text = ""
        match_tag = cols[2].find("b")
        if match_tag:
            match_text = match_tag.get_text(strip=True)
        liga, _ = parse_league_and_teams(liga_text)
        equipos = match_text or liga_text

        try:
            dt_source = datetime.strptime(f"{base_date} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            continue
        dt_arg = dt_source + timedelta(hours=2)
        date_offset = (dt_arg.date() - dt_source.date()).days

        canales: List[Dict[str, Any]] = []
        for link in cols[2].find_all("a", href=True):
            href = link.get("href") or ""
            if not href:
                continue
            full_url = make_abs_url(PIRLOTV_URL, href)
            iframe_url = ""
            try:
                channel_html = fetch_html(session, full_url)
                iframe_url = extract_iframe_src(channel_html)
                iframe_url = make_abs_url(full_url, iframe_url)
            except Exception:
                iframe_url = ""
            canales.append({
                "nombre": channel_name_from_url(full_url) or "PirloTV",
                "url": iframe_url or full_url,
                "calidad": "",
            })

        events.append(build_event(dt_arg, "", liga, equipos, canales, date_offset))

    return events


def parse_tvlibree(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        html_text = fetch_html(session, TVLIBREE_URL)
    except Exception as exc:
        logger.error("tvlibree error: %s", exc)
        return events

    page_date = find_date_in_text(html_text)
    base_date = (page_date.date() if page_date else today_arg_date().date())

    soup = BeautifulSoup(html_text, "html.parser")
    for item in soup.find_all("li"):
        time_span = item.find("span", class_="t")
        if not time_span:
            continue
        time_str = time_span.get_text(strip=True)
        if not time_str:
            continue
        main_link = item.find("a")
        if not main_link:
            continue
        title_text = normalize_ws(main_link.get_text(" ", strip=True))
        liga, equipos = parse_league_and_teams(title_text)
        logo = ""
        flag_img = item.find("img")
        if flag_img and flag_img.get("src"):
            logo = flag_img.get("src")

        try:
            dt_source = datetime.strptime(f"{base_date} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            continue
        dt_arg = dt_source - timedelta(hours=4)
        date_offset = (dt_arg.date() - dt_source.date()).days

        canales: List[Dict[str, Any]] = []
        for subitem in item.find_all("li", class_="subitem1"):
            link = subitem.find("a", href=True)
            if not link:
                continue
            href = link.get("href") or ""
            label = normalize_ws(link.get_text(" ", strip=True))
            if href.startswith("/eventos/"):
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                decoded = decode_base64(qs.get("r", [""])[0])
                if decoded:
                    canales.append({"nombre": label, "url": decoded, "calidad": ""})
                continue
            if href.startswith("/en-vivo/"):
                full_url = make_abs_url("https://tvlibree.com/", href)
                try:
                    detail_html = fetch_html(session, full_url)
                    option_urls = extract_onclick_urls(detail_html)
                except Exception:
                    option_urls = []
                for option_url in option_urls:
                    if option_url.startswith("/html/fl/"):
                        option_url = make_abs_url("https://tvlibree.com/", option_url)
                    if not filter_bad_tvlibree_url(option_url):
                        continue
                    canales.append({"nombre": label, "url": option_url, "calidad": ""})
                continue
            full_url = make_abs_url("https://tvlibree.com/", href)
            if filter_bad_tvlibree_url(full_url):
                canales.append({"nombre": label, "url": full_url, "calidad": ""})

        events.append(build_event(dt_arg, logo, liga, equipos, canales, date_offset))

    return events


def parse_tvtvhd(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        html_text = fetch_html(session, TVTVHD_URL)
    except Exception as exc:
        logger.error("tvtvhd error: %s", exc)
        return events

    page_date = find_date_in_text(html_text)
    base_date = (page_date.date() if page_date else today_arg_date().date())

    soup = BeautifulSoup(html_text, "html.parser")
    menu = soup.find("ul", id="menu")
    if not menu:
        return events

    for item in menu.find_all("li", class_="toggle-submenu"):
        time_tag = item.find("time")
        time_str = time_tag.get_text(strip=True) if time_tag else ""
        if not time_str:
            continue
        title_span = item.find("span")
        title_text = normalize_ws(title_span.get_text(" ", strip=True) if title_span else "")
        liga, equipos = parse_league_and_teams(title_text)
        logo = ""
        flag_img = item.find("img")
        if flag_img and flag_img.get("src"):
            logo = flag_img.get("src")

        try:
            dt_arg = datetime.strptime(f"{base_date} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            continue
        date_offset = 0

        canales: List[Dict[str, Any]] = []
        for link in item.find_all("a", href=True):
            href = link.get("href") or ""
            label = normalize_ws(link.get_text(" ", strip=True))
            if "/embed/eventos.html" in href:
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                decoded = decode_base64(qs.get("r", [""])[0])
                if decoded:
                    canales.append({"nombre": label, "url": decoded, "calidad": ""})
                else:
                    canales.append({"nombre": label, "url": make_abs_url("https://tvtvhd.com/", href), "calidad": ""})

        events.append(build_event(dt_arg, logo, liga, equipos, canales, date_offset))

    return events


def normalize_text(text: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin acentos, sin espacios extra."""
    import unicodedata
    text = text.lower().strip()
    # Remover acentos
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Remover caracteres especiales y espacios múltiples
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def event_key(event: Dict[str, Any]) -> Tuple[str, str]:
    """
    Genera una clave única para identificar eventos duplicados.
    Usa equipos normalizados + hora UTC (redondeada a 15 min).
    """
    equipos = normalize_text(event.get("equipos", ""))
    hora_utc = event.get("hora_utc", "")
    
    # Redondear hora a bloques de 15 min para tolerar diferencias pequeñas
    if hora_utc:
        try:
            dt = datetime.fromisoformat(hora_utc.replace("Z", "+00:00"))
            # Redondear a 15 minutos
            minutes = (dt.minute // 15) * 15
            dt = dt.replace(minute=minutes, second=0, microsecond=0)
            hora_utc = dt.isoformat()
        except:
            pass
    
    return (equipos, hora_utc)


def merge_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fusiona eventos duplicados acoplando sus canales.
    """
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    
    for event in events:
        key = event_key(event)
        
        if key in merged:
            # Fusionar canales
            existing = merged[key]
            existing_urls = {ch.get("url") for ch in existing.get("canales", [])}
            
            for new_ch in event.get("canales", []):
                if new_ch.get("url") not in existing_urls:
                    existing["canales"].append(new_ch)
                    existing_urls.add(new_ch.get("url"))
            
            # Si el existente no tiene logo pero el nuevo sí, usar el nuevo
            if not existing.get("logo") and event.get("logo"):
                existing["logo"] = event["logo"]
            
            # Si el existente no tiene liga pero el nuevo sí, usar el nuevo
            if not existing.get("liga") and event.get("liga"):
                existing["liga"] = event["liga"]
        else:
            # Nuevo evento, clonar para evitar modificar el original
            merged[key] = {
                "hora_utc": event.get("hora_utc", ""),
                "hora_argentina": event.get("hora_argentina", ""),
                "logo": event.get("logo", ""),
                "liga": event.get("liga", ""),
                "equipos": event.get("equipos", ""),
                "canales": list(event.get("canales", [])),
                "date_offset": event.get("date_offset", 0),
            }
    
    return list(merged.values())


def build_all_events() -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })

    all_events: List[Dict[str, Any]] = []
    all_events.extend(parse_elcanaldeportivo(session))
    all_events.extend(parse_streamx10(session))
    all_events.extend(parse_bolaloca(session))
    all_events.extend(parse_antenasport(session))
    all_events.extend(parse_pirlotvoficial(session))
    all_events.extend(parse_tvlibree(session))
    all_events.extend(parse_tvtvhd(session))

    # Deduplicar y fusionar canales de eventos iguales
    logger.info("Eventos antes de deduplicar: %d", len(all_events))
    all_events = merge_events(all_events)
    logger.info("Eventos después de deduplicar: %d", len(all_events))

    all_events.sort(key=lambda x: x.get("hora_utc", ""))
    return all_events


def sync_to_github(json_path: Path) -> None:
    """Copia el JSON al repositorio y hace push a GitHub."""
    git_dir = REPO_PATH / ".git"
    if not git_dir.is_dir():
        logger.warning("No se encontró repositorio git en %s", REPO_PATH)
        return
    
    dest_path = REPO_PATH / "partidos.json"
    
    # Copiar el archivo al repositorio
    shutil.copyfile(str(json_path), str(dest_path))
    logger.info("Archivo copiado a %s", dest_path)
    
    # Git add
    subprocess.run(["git", "-C", str(REPO_PATH), "add", "partidos.json"], check=False)
    
    # Verificar si hay cambios
    diff_result = subprocess.run(
        ["git", "-C", str(REPO_PATH), "diff", "--cached", "--quiet"],
        check=False
    )
    if diff_result.returncode == 0:
        logger.info("No hay cambios para subir a GitHub")
        return
    
    # Commit
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    subprocess.run(
        ["git", "-C", str(REPO_PATH), "commit", "-m", f"Update partidos.json {timestamp}"],
        check=False,
    )
    logger.info("Commit realizado")
    
    # Push
    push_result = subprocess.run(["git", "-C", str(REPO_PATH), "push"], check=False)
    if push_result.returncode == 0:
        logger.info("Push a GitHub exitoso")
    else:
        logger.error("Error al hacer push a GitHub")


def main() -> None:
    # Sobrescribir completamente el JSON con los nuevos datos
    events = build_all_events()
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    logger.info("Eventos guardados: %s", len(events))
    
    # Subir a GitHub
    sync_to_github(OUTPUT_JSON)


if __name__ == "__main__":
    main()
