"""
Scraper de series desde ww3.animeonline.ninja
Usa DrissionPage (navegador real) para bypassear Cloudflare.
Recibe una URL de serie, extrae info, busca en TMDB, navega episodios
y extrae servidores (excluyendo NETU y FILEMOON).
Guarda/actualiza en series.json en el root del workspace.
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
from DrissionPage import ChromiumPage, ChromiumOptions

# ── Config ──────────────────────────────────────────────────────────────
TMDB_API_KEY = "201d333198374a91c81dba3c443b1a8e"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

EXCLUDED_SERVERS = {"netu", "filemoon"}

LANGUAGE_MAP = {
    "OD_SUB": "SUB",
    "OD_LAT": "LATINO",
    "OD_ES": "Castellano",
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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

    # Completar metadatos faltantes sin borrar los existentes
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

    # Guardar urls de origen
    for url_field in ["animeonline_url", "pelicinehd_url", "series24_url"]:
        if new_serie.get(url_field):
            current[url_field] = new_serie[url_field]

    # Mantener created_at existente
    if not current.get("created_at") and new_serie.get("created_at"):
        current["created_at"] = new_serie["created_at"]
    current["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Fusionar episodios
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


class AnimeOnlineScraper:
    def __init__(self):
        self.browser: Optional[ChromiumPage] = None
        self.delay = 1.5  # segundos entre navegaciones

    # ── Browser ──────────────────────────────────────────────────────────

    def _init_browser(self):
        """Inicializa el navegador si no está activo."""
        if self.browser is None:
            logger.info("Iniciando navegador...")
            co = ChromiumOptions()
            co.set_argument("--disable-gpu")
            co.set_argument("--no-sandbox")
            self.browser = ChromiumPage(co)
            logger.info("Navegador listo")

    def _close_browser(self):
        """Cierra el navegador."""
        if self.browser:
            try:
                self.browser.quit()
            except Exception:
                pass
            self.browser = None

    def _navigate(self, url: str, wait_cf: bool = True) -> str:
        """
        Navega a una URL, espera que pase Cloudflare si es necesario,
        y devuelve el HTML de la página.
        """
        self._init_browser()
        time.sleep(self.delay)
        logger.info(f"GET {url}")
        self.browser.get(url)

        if wait_cf:
            self._wait_cloudflare()

        return self.browser.html

    def _wait_cloudflare(self, max_wait: int = 40):
        """Espera a que la página pase el desafío de Cloudflare."""
        for i in range(max_wait // 2):
            title = self.browser.title.lower()
            if "momento" not in title and "moment" not in title:
                return
            time.sleep(2)
        logger.warning("Cloudflare timeout - la página puede no haber cargado bien")

    def _navigate_simple(self, url: str) -> str:
        """
        Navega a una URL sin protección Cloudflare (ej: iframe de saidochesto).
        Usa requests directamente ya que estos sitios no tienen CF.
        """
        time.sleep(0.5)
        logger.info(f"GET (directo) {url}")
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                },
                timeout=15,
            )
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            logger.warning(f"Error en request simple a {url}: {e}")
            # Fallback: usar el navegador
            return self._navigate(url, wait_cf=False)

    def _workspace_root(self) -> str:
        return _workspace_root()

    # ── TMDB ─────────────────────────────────────────────────────────────

    def search_tmdb(self, title: str) -> Optional[Dict]:
        return tmdb_search(title)

    def _get_tmdb_details(self, tmdb_id: int) -> Optional[Dict]:
        return tmdb_details(tmdb_id)

    # ── Parseo de la página principal de la serie ────────────────────────

    def parse_series_page(self, url: str) -> Dict:
        """Extrae título, poster, géneros y lista de episodios de la página de la serie."""
        html = self._navigate(url)
        soup = BeautifulSoup(html, "html.parser")

        # Título
        title_tag = soup.select_one(".sheader .data h1")
        title = title_tag.get_text(strip=True) if title_tag else "Sin título"

        # Poster
        poster_tag = soup.select_one(".sheader .poster img")
        poster_url = ""
        if poster_tag:
            poster_url = poster_tag.get("data-src") or poster_tag.get("src", "")

        # Rating
        rating = 0
        rating_tag = soup.select_one(".dt_rating_vgs")
        if rating_tag:
            try:
                rating = float(rating_tag.get_text(strip=True))
            except ValueError:
                pass

        # Episodios
        episodes_info = []
        season_divs = soup.select("#seasons .se-c")
        for sdiv in season_divs:
            season_num_tag = sdiv.select_one(".se-t")
            season_num = 1
            if season_num_tag:
                try:
                    season_num = int(season_num_tag.get_text(strip=True))
                except ValueError:
                    pass

            ep_items = sdiv.select("ul.episodios li")
            for li in ep_items:
                num_div = li.select_one(".numerando")
                title_a = li.select_one(".episodiotitle a")

                if not num_div or not title_a:
                    continue

                num_text = num_div.get_text(strip=True)  # "1 - 3"
                parts = num_text.split("-")
                ep_num = 1
                if len(parts) >= 2:
                    try:
                        ep_num = int(parts[1].strip())
                    except ValueError:
                        pass

                ep_title = title_a.get_text(strip=True)
                ep_url = title_a.get("href", "")

                episodes_info.append({
                    "season": season_num,
                    "episode": ep_num,
                    "title": ep_title,
                    "url": ep_url,
                })

        return {
            "title": title,
            "poster_url": poster_url,
            "rating": rating,
            "episodes": episodes_info,
        }

    # ── Extraer iframe de la página del episodio ─────────────────────────

    def get_episode_iframe(self, episode_url: str) -> Optional[str]:
        """Visita la página del episodio y espera a que cargue el iframe dinámico."""
        try:
            self._navigate(episode_url)

            # El iframe se carga dinámicamente via JS, hay que esperar a que aparezca
            for attempt in range(15):  # máximo ~15 segundos
                try:
                    el = self.browser.ele("css:iframe.metaframe", timeout=1)
                    if el:
                        src = el.attr("src")
                        if src:
                            return src
                except Exception:
                    pass

                try:
                    el = self.browser.ele("css:#dooplay_player_response iframe", timeout=1)
                    if el:
                        src = el.attr("src")
                        if src:
                            return src
                except Exception:
                    pass

                try:
                    el = self.browser.ele("css:.pframe iframe", timeout=1)
                    if el:
                        src = el.attr("src")
                        if src:
                            return src
                except Exception:
                    pass

                time.sleep(1)

            logger.warning(f"Iframe no apareció tras 15s en {episode_url}")

        except Exception as e:
            logger.warning(f"Error obteniendo iframe de {episode_url}: {e}")
        return None

    # ── Extraer servidores del iframe ────────────────────────────────────

    def get_servers_from_iframe(self, iframe_url: str) -> List[Dict]:
        """
        Obtiene el HTML del iframe (saidochesto, etc.) y extrae los servidores.
        Excluye NETU y FILEMOON.
        El iframe NO tiene Cloudflare, así que usamos requests directo.
        """
        servers = []
        try:
            html = self._navigate_simple(iframe_url)
            soup = BeautifulSoup(html, "html.parser")

            for lang_class, lang_label in LANGUAGE_MAP.items():
                section = soup.select_one(f".OD.{lang_class}")
                if not section:
                    continue

                lis = section.select("li[onclick]")
                for li in lis:
                    onclick = li.get("onclick", "")
                    m = re.search(r"go_to_player\(['\"](.+?)['\"]\)", onclick)
                    if not m:
                        continue

                    embed_url = m.group(1)
                    span = li.select_one("span")
                    server_name = span.get_text(strip=True).upper() if span else "UNKNOWN"

                    # Excluir NETU y FILEMOON
                    if server_name.lower() in EXCLUDED_SERVERS:
                        continue

                    server_key = self._normalize_server_name(server_name, embed_url)

                    servers.append({
                        "url": embed_url,
                        "name": server_name,
                        "server": server_key,
                        "language": lang_label,
                    })

        except Exception as e:
            logger.warning(f"Error extrayendo servidores de {iframe_url}: {e}")

        return servers

    def _normalize_server_name(self, name: str, url: str) -> str:
        """Normaliza nombre del servidor."""
        name_lower = name.lower()
        mapping = {
            "streamwish": "streamwish",
            "earnvids": "filelions",
            "filelions": "filelions",
            "mixdrop": "mixdrop",
            "streamtape": "streamtape",
            "lulustream": "lulustream",
            "hexupload": "hexupload",
            "mp4upload": "mp4upload",
            "uqload": "uqload",
            "okru": "okru",
            "doodstream": "doodstream",
            "dood": "doodstream",
            "voe": "voe",
        }
        for key, val in mapping.items():
            if key in name_lower:
                return val

        domain_mapping = {
            "streamwish": "streamwish",
            "filelions": "filelions",
            "mixdrop": "mixdrop",
            "mxdrop": "mixdrop",
            "mixdropjmk": "mixdrop",
            "streamtape": "streamtape",
            "luluvdo": "lulustream",
            "hexupload": "hexupload",
            "hexload": "hexupload",
            "mp4upload": "mp4upload",
            "uqload": "uqload",
            "ok.ru": "okru",
            "dood": "doodstream",
        }
        url_lower = url.lower()
        for key, val in domain_mapping.items():
            if key in url_lower:
                return val

        return name_lower.replace(" ", "")

    # ── Proceso principal ────────────────────────────────────────────────

    def scrape_series(self, series_url: str) -> Dict:
        """
        Proceso completo:
        1. Parsear página de la serie (con navegador, bypasea CF)
        2. Buscar en TMDB
        3. Para cada episodio, obtener iframe y servidores
        4. Armar el objeto final
        """
        logger.info(f"{'='*60}")
        logger.info(f"Iniciando scraping de: {series_url}")
        logger.info(f"{'='*60}")

        try:
            # 1. Parsear página principal
            page_data = self.parse_series_page(series_url)
            title = page_data["title"]
            logger.info(f"Serie: {title}")
            logger.info(f"Episodios encontrados: {len(page_data['episodes'])}")

            # 2. Buscar en TMDB
            logger.info(f"Buscando '{title}' en TMDB...")
            tmdb_data = self.search_tmdb(title)

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
                    "number_of_seasons": 1,
                    "number_of_episodes": len(page_data["episodes"]),
                }

            # 3. Procesar cada episodio
            episodios = []
            total = len(page_data["episodes"])

            for i, ep_info in enumerate(page_data["episodes"], 1):
                ep_url = ep_info["url"]
                logger.info(
                    f"  [{i}/{total}] S{ep_info['season']:02d}E{ep_info['episode']:03d}: "
                    f"{ep_info['title'][:50]}"
                )

                if not ep_url:
                    logger.warning("    Sin URL, saltando...")
                    continue

                # Obtener iframe
                iframe_url = self.get_episode_iframe(ep_url)
                if not iframe_url:
                    logger.warning("    No se encontró iframe, saltando...")
                    continue

                logger.info(f"    Iframe: {iframe_url}")

                # Obtener servidores del iframe (requests directo, sin CF)
                servers = self.get_servers_from_iframe(iframe_url)
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

            # 4. Armar objeto final
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
                "number_of_seasons": tmdb_data["number_of_seasons"],
                "number_of_episodes": tmdb_data["number_of_episodes"],
                "animeonline_url": series_url,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "episodios": episodios,
            }

            logger.info(f"{'='*60}")
            logger.info(f"Completado: {len(episodios)} episodios con servidores")
            logger.info(f"{'='*60}")
            return serie

        finally:
            self._close_browser()

    def save_to_json(self, serie: Dict, output_path: Optional[str] = None):
        if output_path:
            save_series_json(serie, output_path)
        else:
            save_series_json(serie)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Uso: python scraper_animeonline_series.py <URL_SERIE>")
        print()
        print("Ejemplo:")
        print("  python scraper_animeonline_series.py https://ww3.animeonline.ninja/online/dragon-ball-super-3-082125/")
        print()
        print("El scraper:")
        print("  1. Abre la serie en el navegador (bypasea Cloudflare)")
        print("  2. Extrae titulo, episodios")
        print("  3. Busca info en TMDB")
        print("  4. Navega cada episodio, extrae iframe y servidores")
        print("  5. Excluye NETU y FILEMOON")
        print("  6. Guarda en series.json")
        sys.exit(1)

    series_url = sys.argv[1]
    scraper = AnimeOnlineScraper()

    serie = scraper.scrape_series(series_url)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  Serie: {serie['name']}")
    print(f"  TMDB ID: {serie['tmdb_id']}")
    print(f"  Episodios: {len(serie['episodios'])}")
    total_servers = sum(len(ep["servidores"]) for ep in serie["episodios"])
    print(f"  Total servidores: {total_servers}")
    print(f"{'='*60}\n")

    scraper.save_to_json(serie)


if __name__ == "__main__":
    main()
