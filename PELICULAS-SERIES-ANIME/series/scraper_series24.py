"""
Scraper de temporadas desde series24.one
- Recibe URL de temporada (ej: https://www.series24.one/temporada/en-el-barro-temporada-2/)
- Busca la serie en TMDB y completa metadatos
- Extrae episodios y servidores via dooplay (excluye streamplay, filemoon, powvideo)
- Fusiona resultados en series.json (no sobrescribe episodios existentes)
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

TMDB_API_KEY = "201d333198374a91c81dba3c443b1a8e"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

SERIES24_BASE_URL = "https://www.series24.one"
SERIES24_EXCLUDED_SERVERS = {"streamplay", "filemoon", "powvideo"}
SERIES24_LANGUAGE_MAP = {
    "embed-mx": "LAT",
    "embed-es": "ESP",
    "embed-jp": "SUB",
    "embed-en": "ENG",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Helpers -----------------------------------------------------------------

def _workspace_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", ".."))


def _load_series(output_path: Optional[str] = None) -> List[Dict]:
    if not output_path:
        output_path = os.path.join(_workspace_root(), "series.json")
    if not os.path.exists(output_path):
        return []
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def merge_series(existing: List[Dict], new_serie: Dict) -> List[Dict]:
    target_idx = None

    def _matches(a: Dict, b: Dict) -> bool:
        if a.get("tmdb_id") and b.get("tmdb_id") and a.get("tmdb_id") == b.get("tmdb_id"):
            return True
        a_name = (a.get("name") or "").strip().lower()
        b_name = (b.get("name") or "").strip().lower()
        return a_name and a_name == b_name

    for idx, serie in enumerate(existing):
        if _matches(serie, new_serie):
            target_idx = idx
            break

    if target_idx is None:
        new_serie["updated_at"] = datetime.now(timezone.utc).isoformat()
        existing.append(new_serie)
        return existing

    current = existing[target_idx]
    current.setdefault("episodios", [])

    fields = [
        "original_name",
        "overview",
        "poster_path",
        "backdrop_path",
        "first_air_date",
        "genres",
        "vote_average",
        "vote_count",
        "popularity",
        "status",
        "number_of_seasons",
        "number_of_episodes",
    ]
    for key in fields:
        if not current.get(key) and new_serie.get(key):
            current[key] = new_serie[key]

    for url_field in ["animeonline_url", "pelicinehd_url", "series24_url"]:
        if new_serie.get(url_field):
            current[url_field] = new_serie[url_field]

    if not current.get("created_at") and new_serie.get("created_at"):
        current["created_at"] = new_serie["created_at"]
    current["updated_at"] = datetime.now(timezone.utc).isoformat()

    eps = current.get("episodios", [])
    for new_ep in new_serie.get("episodios", []):
        match = next(
            (
                ep
                for ep in eps
                if ep.get("season") == new_ep.get("season") and ep.get("episode") == new_ep.get("episode")
            ),
            None,
        )

        if not match:
            eps.append(new_ep)
            continue

        if not match.get("title") and new_ep.get("title"):
            match["title"] = new_ep["title"]

        existing_urls = {srv.get("url") for srv in match.get("servidores", []) if srv.get("url")}
        for srv in new_ep.get("servidores", []):
            if srv.get("url") and srv["url"] in existing_urls:
                continue
            match.setdefault("servidores", []).append(srv)

    current["episodios"] = eps
    existing[target_idx] = current
    return existing


def save_series_json(serie: Dict, output_path: Optional[str] = None):
    if not output_path:
        output_path = os.path.join(_workspace_root(), "series.json")

    existing = _load_series(output_path)
    updated = merge_series(existing, serie)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    logger.info(f"Guardado en: {output_path}")
    logger.info(f"Total series en archivo: {len(updated)}")


def tmdb_details(tmdb_id: int) -> Optional[Dict]:
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "es-ES"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        d = resp.json()
        genres = [g["name"] for g in d.get("genres", [])]
        return {
            "tmdb_id": d.get("id"),
            "name": d.get("name", ""),
            "original_name": d.get("original_name", ""),
            "overview": d.get("overview", ""),
            "poster_path": f"https://image.tmdb.org/t/p/w500{d['poster_path']}" if d.get("poster_path") else "",
            "backdrop_path": f"https://image.tmdb.org/t/p/original{d['backdrop_path']}" if d.get("backdrop_path") else "",
            "first_air_date": d.get("first_air_date", ""),
            "genres": genres,
            "vote_average": d.get("vote_average", 0),
            "vote_count": d.get("vote_count", 0),
            "popularity": d.get("popularity", 0),
            "status": d.get("status", ""),
            "number_of_seasons": d.get("number_of_seasons", 1),
            "number_of_episodes": d.get("number_of_episodes", 0),
        }
    except Exception as e:
        logger.error(f"Error obteniendo detalles TMDB {tmdb_id}: {e}")
    return None


def tmdb_search(title: str) -> Optional[Dict]:
    url = f"{TMDB_BASE_URL}/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "es-ES",
        "query": title,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if not results:
            simple = re.sub(r"\s*\d+$", "", title).strip()
            if simple != title:
                params["query"] = simple
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                results = data.get("results", [])
        if results:
            best = results[0]
            return tmdb_details(best["id"])
    except Exception as e:
        logger.error(f"Error buscando en TMDB '{title}': {e}")
    return None


# Scraper -----------------------------------------------------------------

class Series24Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })

    def _get(self, url: str) -> str:
        resp = self.session.get(url, timeout=20)
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            logger.warning(f"GET {url} -> {resp.status_code}")
        return resp.text

    def _post_player(self, post_id: str, nume: str, player_type: str, referer: str) -> str:
        if not post_id or not nume:
            return ""
        data = {
            "action": "doo_player_ajax",
            "post": post_id,
            "nume": nume,
            "type": player_type or "tv",
        }
        headers = {
            "Referer": referer,
            "Origin": SERIES24_BASE_URL,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.session.headers.get("User-Agent", ""),
        }
        try:
            resp = self.session.post(
                f"{SERIES24_BASE_URL}/wp-admin/admin-ajax.php",
                data=data,
                headers=headers,
                timeout=20,
            )
            resp.encoding = "utf-8"
            return resp.text
        except Exception as exc:
            logger.warning(f"Error solicitando player {post_id}-{nume}: {exc}")
            return ""

    def _clean_title(self, raw_title: str) -> str:
        cleaned = re.sub(r":?\s*Temporada\s+\d+", "", raw_title, flags=re.IGNORECASE)
        return cleaned.strip(" :-") or raw_title

    def _language_for_tab(self, tab_id: Optional[str]) -> str:
        if not tab_id:
            return "LAT"
        return SERIES24_LANGUAGE_MAP.get(tab_id, "LAT")

    def _normalize_server_name(self, name: str, url: str) -> str:
        name_lower = (name or "").lower()
        mapping = {
            "luluvid": "lulustream",
            "lulustream": "lulustream",
            "lulu": "lulustream",
            "dsvplay": "dsvplay",
            "streamtape": "streamtape",
            "voe": "voe",
        }
        for key, val in mapping.items():
            if key in name_lower:
                return val
        domain_mapping = {
            "lulustream": "lulustream",
            "luluvid": "lulustream",
            "dsvplay": "dsvplay",
            "streamtape": "streamtape",
            "voe": "voe",
        }
        url_lower = (url or "").lower()
        for key, val in domain_mapping.items():
            if key in url_lower:
                return val
        return name_lower.replace(" ", "")

    def _extract_iframe(self, html_text: str) -> str:
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        iframe = soup.find("iframe")
        return iframe.get("src", "") if iframe else ""

    def parse_season_page(self, url: str) -> Dict:
        html = self._get(url)
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.select_one(".sheader .data h1")
        raw_title = title_tag.get_text(strip=True) if title_tag else "Sin titulo"
        clean_title = self._clean_title(raw_title)

        poster_tag = soup.select_one(".sheader .poster img")
        poster_url = ""
        if poster_tag:
            poster_url = poster_tag.get("data-src") or poster_tag.get("src", "")

        rating = 0.0
        rating_tag = soup.select_one(".dt_rating_vgs")
        if rating_tag:
            try:
                rating = float(rating_tag.get_text(strip=True))
            except Exception:
                rating = 0.0

        episodes_info = []
        li_nodes = soup.select("#loadEpisodes ul.episodios li") or soup.select("ul.episodios li")
        for li in li_nodes:
            num_div = li.select_one(".numerando")
            title_a = li.select_one(".episodiotitle a")
            if not num_div or not title_a:
                continue

            num_text = num_div.get_text(strip=True)
            parts = [p.strip() for p in num_text.split("-") if p.strip()]
            season_num = 1
            ep_num = 1
            if len(parts) >= 1:
                try:
                    season_num = int(parts[0])
                except Exception:
                    season_num = 1
            if len(parts) >= 2:
                try:
                    ep_num = int(parts[1])
                except Exception:
                    ep_num = 1

            ep_title = title_a.get_text(strip=True) or f"Episodio {ep_num}"
            ep_url = title_a.get("href", "")

            episodes_info.append({
                "season": season_num,
                "episode": ep_num,
                "title": ep_title,
                "url": ep_url,
            })

        if not episodes_info:
            try:
                debug_dir = os.path.join(_workspace_root(), "debug")
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, "series24_page.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning("No se encontraron episodios; HTML guardado en debug/series24_page.html")
            except Exception:
                pass

        season_guess = None
        if episodes_info:
            season_guess = episodes_info[0].get("season")
        if not season_guess:
            m = re.search(r"temporada[-/](\d+)", url)
            if m:
                try:
                    season_guess = int(m.group(1))
                except Exception:
                    season_guess = None

        return {
            "title": clean_title,
            "raw_title": raw_title,
            "poster_url": poster_url,
            "rating": rating,
            "season": season_guess or 1,
            "episodes": episodes_info,
        }

    def fetch_episode_servers(self, episode_url: str) -> List[Dict]:
        servers: List[Dict] = []
        try:
            html = self._get(episode_url)
            soup = BeautifulSoup(html, "html.parser")

            option_nodes = soup.select("div[id^=embed-] li.dooplay_player_option")
            for li in option_nodes:
                server_name = ""
                name_span = li.select_one("span.title")
                if name_span:
                    server_name = name_span.get_text(strip=True)
                server_name_lower = server_name.lower()
                if server_name_lower in SERIES24_EXCLUDED_SERVERS:
                    continue

                parent_tab = li.find_parent("div", id=re.compile(r"^embed-"))
                lang_id = parent_tab.get("id") if parent_tab else ""
                language = self._language_for_tab(lang_id)

                post_id = li.get("data-post") or li.get("data-postid") or ""
                nume = li.get("data-nume") or li.get("data-id") or ""
                player_type = li.get("data-type", "tv")

                embed_html = self._post_player(post_id, nume, player_type, episode_url)
                iframe_src = self._extract_iframe(embed_html)
                if not iframe_src:
                    continue

                server_key = self._normalize_server_name(server_name, iframe_src)

                servers.append({
                    "url": iframe_src,
                    "name": server_name,
                    "server": server_key,
                    "language": language,
                })

        except Exception as exc:
            logger.warning(f"Error extrayendo servidores de {episode_url}: {exc}")

        unique_urls = set()
        deduped = []
        for srv in servers:
            url_val = srv.get("url")
            if not url_val or url_val in unique_urls:
                continue
            unique_urls.add(url_val)
            deduped.append(srv)
        return deduped

    def scrape_series(self, season_url: str) -> Dict:
        logger.info(f"{'='*60}")
        logger.info(f"Iniciando scraping de Series24: {season_url}")
        logger.info(f"{'='*60}")

        page_data = self.parse_season_page(season_url)
        title = page_data["title"]
        logger.info(f"Serie: {title}")
        logger.info(f"Episodios encontrados: {len(page_data['episodes'])}")

        tmdb_data = tmdb_search(title)
        if tmdb_data:
            logger.info(f"TMDB encontrado: {tmdb_data['name']} (ID: {tmdb_data['tmdb_id']})")
        else:
            logger.warning("No se encontró en TMDB, usando datos locales")
            tmdb_data = {
                "tmdb_id": 0,
                "name": title,
                "original_name": title,
                "overview": "",
                "poster_path": page_data["poster_url"],
                "backdrop_path": "",
                "first_air_date": "",
                "genres": [],
                "vote_average": page_data["rating"],
                "vote_count": 0,
                "popularity": 0,
                "status": "Unknown",
                "number_of_seasons": page_data["season"],
                "number_of_episodes": len(page_data["episodes"]),
            }

        episodios = []
        total = len(page_data["episodes"])
        for i, ep_info in enumerate(page_data["episodes"], 1):
            ep_url = ep_info.get("url", "")
            logger.info(
                f"  [{i}/{total}] S{ep_info['season']:02d}E{ep_info['episode']:03d}: {ep_info['title'][:50]}"
            )
            if not ep_url:
                logger.warning("    Sin URL, saltando...")
                continue

            servers = self.fetch_episode_servers(ep_url)
            logger.info(f"    Servidores: {len(servers)}")

            if servers:
                episodios.append({
                    "season": ep_info["season"],
                    "episode": ep_info["episode"],
                    "title": ep_info["title"],
                    "servidores": servers,
                })
            else:
                logger.warning("    Sin servidores válidos")

        serie = {
            "tmdb_id": tmdb_data["tmdb_id"],
            "name": tmdb_data["name"],
            "original_name": tmdb_data["original_name"],
            "overview": tmdb_data["overview"],
            "poster_path": tmdb_data["poster_path"],
            "backdrop_path": tmdb_data["backdrop_path"],
            "first_air_date": tmdb_data["first_air_date"],
            "genres": tmdb_data["genres"],
            "vote_average": tmdb_data["vote_average"],
            "vote_count": tmdb_data["vote_count"],
            "popularity": tmdb_data["popularity"],
            "status": tmdb_data["status"],
            "number_of_seasons": max(tmdb_data.get("number_of_seasons", 1), page_data["season"]),
            "number_of_episodes": tmdb_data.get("number_of_episodes", len(episodios)),
            "series24_url": season_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "episodios": episodios,
        }

        logger.info(f"{'='*60}")
        logger.info(f"Completado Series24: {len(episodios)} episodios con servidores")
        logger.info(f"{'='*60}")
        return serie

    def save_to_json(self, serie: Dict, output_path: Optional[str] = None):
        if output_path:
            save_series_json(serie, output_path)
        else:
            save_series_json(serie)


# CLI ---------------------------------------------------------------------

def main():
    import sys

    if len(sys.argv) < 2:
        print("Uso: python scraper_series24.py <URL_TEMPORADA_SERIES24>")
        print()
        print("Ejemplo:")
        print("  python scraper_series24.py https://www.series24.one/temporada/en-el-barro-temporada-2/")
        print()
        print("El scraper:")
        print("  1. Lee la página de temporada en series24.one")
        print("  2. Busca la serie en TMDB y completa metadatos")
        print("  3. Recorre episodios, resuelve players (excluye streamplay/filemoon/powvideo)")
        print("  4. Fusiona con series.json sin borrar episodios existentes")
        sys.exit(1)

    season_url = sys.argv[1]
    scraper = Series24Scraper()
    serie = scraper.scrape_series(season_url)

    print(f"\n{'='*60}")
    print(f"  Serie: {serie['name']}")
    print(f"  TMDB ID: {serie['tmdb_id']}")
    print(f"  Episodios: {len(serie['episodios'])}")
    total_servers = sum(len(ep.get('servidores', [])) for ep in serie["episodios"])
    print(f"  Total servidores: {total_servers}")
    print(f"{'='*60}\n")

    scraper.save_to_json(serie)


if __name__ == "__main__":
    main()
