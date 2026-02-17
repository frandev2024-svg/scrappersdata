"""
Scraper de series desde poseidonhd2.co/series
Navega por grids, entra a cada serie, y extrae temporadas, episodios y servidores.
Guarda y actualiza series.json en el root del workspace.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configuracion
POSEIDON_BASE_URL = "https://www.poseidonhd2.co"
SERIES_URL = f"{POSEIDON_BASE_URL}/series"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PoseidonSeriesScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        self.series: List[Dict] = []
        self.processed_series_ids = set()
        self.debug_season_url: Optional[str] = None
        self.debug_episode_url: Optional[str] = None
        self.next_build_id: Optional[str] = None

    def _get_html(self, url: str, referer: Optional[str] = None, timeout: int = 15) -> str:
        """Obtiene HTML usando headers similares al navegador."""
        headers = {}
        if referer:
            headers["Referer"] = referer
            headers["Origin"] = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
        response = self.session.get(url, timeout=timeout, headers=headers or None)
        response.encoding = "utf-8"
        return response.text

    def _normalize_url(self, url: str) -> str:
        if not url:
            return url
        url = url.replace("\\/", "/")
        url = url.replace("&amp;", "&")
        return url

    def _workspace_root(self) -> str:
        """Devuelve la ruta base del workspace (dos niveles arriba)."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(script_dir, "..", ".."))

    def _write_debug_file(self, filename: str, content: str) -> None:
        try:
            debug_dir = os.path.join(self._workspace_root(), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            full_path = os.path.join(debug_dir, filename)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"DEBUG guardado: {full_path}")
        except Exception as exc:
            logger.debug(f"No se pudo guardar debug {filename}: {exc}")

    def _get_next_data(self, html_text: str) -> Optional[Dict]:
        """Extrae el JSON de __NEXT_DATA__."""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if script:
                content = script.string if script.string else script.get_text(strip=False)
                if content:
                    data = json.loads(content)
                    build_id = data.get("buildId") if isinstance(data, dict) else None
                    if build_id:
                        self.next_build_id = build_id
                    return data
        except Exception as exc:
            logger.debug(f"Error parseando __NEXT_DATA__: {exc}")
        return None

    def _fetch_next_data_json(self, url: str, html_text: Optional[str] = None) -> Optional[Dict]:
        """Intenta obtener el JSON de Next.js via /_next/data/{buildId}/..."""
        try:
            if not html_text:
                html_text = self._get_html(url, referer=POSEIDON_BASE_URL, timeout=15)
            next_data = self._get_next_data(html_text) if html_text else None
            build_id = None
            if isinstance(next_data, dict):
                build_id = next_data.get("buildId")
            if not build_id:
                build_id = self.next_build_id

            if not build_id:
                return None

            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            if not path:
                return None

            data_url = f"{parsed.scheme}://{parsed.netloc}/_next/data/{build_id}{path}.json"
            json_text = self._get_html(data_url, referer=url, timeout=15)
            if self.debug_season_url and url.rstrip("/") == self.debug_season_url.rstrip("/"):
                self._write_debug_file("next_data_season.json", json_text)
            return json.loads(json_text)
        except Exception as exc:
            logger.debug(f"Error obteniendo _next/data json para {url}: {exc}")
        return None

    def _find_dict_with_keys(self, data, required_keys: List[str]) -> Optional[Dict]:
        """Busca recursivamente un dict que contenga todas las keys requeridas."""
        if isinstance(data, dict):
            if all(k in data for k in required_keys):
                return data
            for value in data.values():
                found = self._find_dict_with_keys(value, required_keys)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_dict_with_keys(item, required_keys)
                if found:
                    return found
        return None

    def _extract_tmdb_id_from_url(self, series_url: str) -> Optional[int]:
        match = re.search(r"/serie/(\d+)/", series_url)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
        return None

    def _extract_season_numbers_from_next_data(self, next_data: Dict) -> List[int]:
        seasons: List[int] = []
        try:
            props = next_data.get("props", {}).get("pageProps", {})
            serie = props.get("serie") if isinstance(props.get("serie"), dict) else None
            season_list = None
            if serie:
                season_list = serie.get("seasons") or serie.get("temporadas")

            if isinstance(season_list, list):
                for item in season_list:
                    if not isinstance(item, dict):
                        continue
                    for key in ["number", "seasonNumber", "season", "num"]:
                        if key in item:
                            try:
                                number = int(item.get(key))
                                if number > 0:
                                    seasons.append(number)
                            except Exception:
                                pass
                            break

            if not seasons:
                container = self._find_dict_with_keys(next_data, ["seasons"])
                if container and isinstance(container.get("seasons"), list):
                    for item in container.get("seasons"):
                        if not isinstance(item, dict):
                            continue
                        for key in ["number", "seasonNumber", "season", "num"]:
                            if key in item:
                                try:
                                    number = int(item.get(key))
                                    if number > 0:
                                        seasons.append(number)
                                except Exception:
                                    pass
                                break
        except Exception:
            return []

        return sorted(set(seasons))

    def _build_episode_url(self, season_url: str, episode_number: Optional[int]) -> str:
        if not episode_number:
            return ""
        match = re.search(r"/temporada/(\d+)", season_url)
        if not match:
            return ""
        season_number = match.group(1)
        base_url = season_url.split("/temporada/")[0]
        return f"{base_url}/temporada/{season_number}/episodio/{episode_number}"

    def _parse_episode_list(self, episodes_list: List[Dict], series_url: str, season_number: int) -> List[Dict]:
        episodes: List[Dict] = []
        if not isinstance(episodes_list, list):
            return episodes
        season_url = f"{series_url}/temporada/{season_number}"

        for item in episodes_list:
            if not isinstance(item, dict):
                continue
            ep_num = None
            for key in ["number", "episode", "episodeNumber", "num"]:
                if key in item:
                    try:
                        ep_num = int(item.get(key))
                    except Exception:
                        ep_num = None
                    break

            title = item.get("title") or item.get("name") or ""
            raw_url = item.get("url") or item.get("link")
            ep_url = ""
            if raw_url and isinstance(raw_url, str):
                ep_url = urljoin(POSEIDON_BASE_URL, raw_url)
            else:
                ep_url = self._build_episode_url(season_url, ep_num)

            if ep_url:
                episodes.append({
                    "url": ep_url,
                    "title": title,
                    "episode": ep_num,
                })

        unique = {}
        for ep in episodes:
            key = ep.get("url") or f"{ep.get('episode')}"
            if key and key not in unique:
                unique[key] = ep
        return list(unique.values())

    def _extract_episodes_from_seasons(self, next_data: Dict, series_url: str, season_number: int) -> List[Dict]:
        """Busca episodios de una temporada en estructuras de seasons dentro de Next data."""
        matches: List[List[Dict]] = []

        def walk(node):
            if isinstance(node, dict):
                if "episodes" in node and isinstance(node.get("episodes"), list):
                    season_num = None
                    for key in ["seasonNumber", "season", "number", "num"]:
                        if key in node:
                            try:
                                season_num = int(node.get(key))
                            except Exception:
                                season_num = None
                            break
                    if season_num == season_number:
                        matches.append(node.get("episodes"))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(next_data)
        episodes: List[Dict] = []
        for ep_list in matches:
            episodes.extend(self._parse_episode_list(ep_list, series_url, season_number))

        unique = {}
        for ep in episodes:
            key = ep.get("url") or f"{ep.get('episode')}"
            if key and key not in unique:
                unique[key] = ep
        return list(unique.values())

    def _extract_episodes_from_next_data(self, next_data: Dict, season_url: str) -> List[Dict]:
        episodes: List[Dict] = []
        episodes_list = None
        props = next_data.get("props", {}).get("pageProps", {}) if isinstance(next_data, dict) else {}

        season_obj = props.get("season") if isinstance(props.get("season"), dict) else None
        if season_obj and isinstance(season_obj.get("episodes"), list):
            episodes_list = season_obj.get("episodes")

        if not episodes_list and isinstance(props.get("episodes"), list):
            episodes_list = props.get("episodes")

        if not episodes_list:
            container = self._find_dict_with_keys(next_data, ["episodes"])
            if container and isinstance(container.get("episodes"), list):
                episodes_list = container.get("episodes")

        if not isinstance(episodes_list, list):
            return episodes

        for item in episodes_list:
            if not isinstance(item, dict):
                continue
            ep_num = None
            for key in ["number", "episode", "episodeNumber", "num"]:
                if key in item:
                    try:
                        ep_num = int(item.get(key))
                    except Exception:
                        ep_num = None
                    break

            title = item.get("title") or item.get("name") or ""
            raw_url = item.get("url") or item.get("link")
            ep_url = ""
            if raw_url:
                ep_url = urljoin(POSEIDON_BASE_URL, raw_url)
            else:
                ep_url = self._build_episode_url(season_url, ep_num)

            if ep_url:
                episodes.append({
                    "url": ep_url,
                    "title": title,
                    "episode": ep_num,
                })

        # Deduplicar
        unique = {}
        for ep in episodes:
            key = ep.get("url") or f"{ep.get('episode')}"
            if key and key not in unique:
                unique[key] = ep
        return list(unique.values())

    def _extract_grid_series(self, page_url: str) -> Tuple[List[Dict], Optional[str]]:
        """Extrae URLs de series desde un grid y devuelve next page si existe."""
        results = []
        next_url = None
        try:
            html_text = self._get_html(page_url, referer=POSEIDON_BASE_URL, timeout=15)
            soup = BeautifulSoup(html_text, "html.parser")

            section = soup.find("section", class_="home-movies")
            if not section:
                logger.warning("No se encontro section.home-movies")
                return results, None

            grid = section.find("ul", class_=re.compile(r"MovieList"))
            if not grid:
                logger.warning("No se encontro ul.MovieList en grid")
                return results, None

            items = grid.find_all("li", class_="TPostMv")
            for item in items:
                a = item.find("a", href=True)
                title_elem = item.find("span", class_="Title")
                year_elem = item.find("span", class_="Year")
                vote_elem = item.find("span", class_="Vote")

                if not a:
                    continue

                href = a.get("href", "")
                series_url = urljoin(POSEIDON_BASE_URL, href)
                results.append({
                    "url": series_url,
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "year": year_elem.get_text(strip=True) if year_elem else "",
                    "vote": vote_elem.get_text(strip=True) if vote_elem else "",
                })

            nav = section.find("nav", class_=re.compile(r"pagination"))
            if nav:
                next_link = nav.find("a", class_=re.compile(r"next"), href=True)
                if next_link:
                    next_url = urljoin(POSEIDON_BASE_URL, next_link["href"])
        except Exception as exc:
            logger.error(f"Error extrayendo grid de {page_url}: {exc}")

        return results, next_url

    def _parse_series_info(self, series_url: str) -> Tuple[Optional[Dict], List[int]]:
        """Extrae informacion de la serie y temporadas disponibles."""
        try:
            html_text = self._get_html(series_url, referer=POSEIDON_BASE_URL, timeout=15)
            soup = BeautifulSoup(html_text, "html.parser")

            title = ""
            original_title = ""
            overview = ""
            genres: List[str] = []
            poster_url = ""
            backdrop_url = ""
            vote_average = 0.0
            vote_count = 0
            popularity = 0.0
            status = ""
            first_air_date = ""

            # Intentar con __NEXT_DATA__ primero
            next_data = self._get_next_data(html_text)
            if next_data:
                serie_data = self._find_dict_with_keys(next_data, ["TMDbId", "titles", "overview"])
                if serie_data:
                    title = serie_data.get("titles", {}).get("name", "")
                    original_title = serie_data.get("titles", {}).get("originalName", "")
                    overview = serie_data.get("overview", "")
                    first_air_date = serie_data.get("releaseDate", "")
                    vote_average = serie_data.get("rate", {}).get("average", 0) or 0
                    vote_count = serie_data.get("rate", {}).get("count", 0) or 0
                    popularity = serie_data.get("popularity", 0) or 0
                    status = serie_data.get("status", "")
                    genres = [g.get("name", "") for g in serie_data.get("genres", []) if g.get("name")]
                    poster_url = serie_data.get("images", {}).get("poster", "")
                    backdrop_url = serie_data.get("images", {}).get("backdrop", "")

            # Fallback HTML
            if not title:
                title_elem = soup.find("h1", class_="Title")
                title = title_elem.get_text(strip=True) if title_elem else ""
            if not original_title:
                subtitle_elem = soup.find("span", class_="SubTitle")
                original_title = subtitle_elem.get_text(strip=True) if subtitle_elem else ""
            if not overview:
                desc = soup.find("div", class_="Description")
                overview = desc.get_text(" ", strip=True) if desc else ""

            if not genres:
                info_list = soup.find("ul", class_="InfoList")
                if info_list:
                    for li in info_list.find_all("li"):
                        if "Genero" in li.get_text():
                            for a in li.find_all("a"):
                                g = a.get_text(strip=True)
                                if g:
                                    genres.append(g)

            if not poster_url:
                poster_img = soup.select_one("article.TPost .Image img")
                poster_url = poster_img.get("src", "") if poster_img else ""
            if not backdrop_url:
                backdrop_img = soup.select_one("div.backdrop > div.Image img")
                backdrop_url = backdrop_img.get("src", "") if backdrop_img else ""

            if not vote_average:
                vote_elem = soup.find("div", id="TPVotes")
                if vote_elem and vote_elem.get("data-percent"):
                    try:
                        vote_average = float(vote_elem.get("data-percent")) / 10.0
                    except Exception:
                        vote_average = 0.0

            year = ""
            meta = soup.find("p", class_="meta")
            if meta:
                spans = meta.find_all("span")
                if spans:
                    year = spans[-1].get_text(strip=True)
                    if year and not first_air_date:
                        first_air_date = f"{year}-01-01"

            season_numbers = []
            select = soup.find("select", id="select-season")
            if select:
                for option in select.find_all("option"):
                    value = option.get("value")
                    try:
                        number = int(value)
                    except Exception:
                        number = None
                    if number and number > 0:
                        season_numbers.append(number)

            if not season_numbers and next_data:
                season_numbers = self._extract_season_numbers_from_next_data(next_data)

            if not season_numbers:
                season_numbers = [1]

            tmdb_id = self._extract_tmdb_id_from_url(series_url)

            info = {
                "tmdb_id": tmdb_id,
                "name": title,
                "original_name": original_title or title,
                "overview": overview,
                "poster_path": poster_url,
                "backdrop_path": backdrop_url,
                "first_air_date": first_air_date,
                "genres": genres,
                "vote_average": vote_average,
                "vote_count": vote_count,
                "popularity": popularity,
                "status": status,
                "number_of_seasons": len(season_numbers),
                "number_of_episodes": 0,
                "pelicinehd_url": series_url,
            }

            return info, season_numbers
        except Exception as exc:
            logger.error(f"Error extrayendo info de serie {series_url}: {exc}")
            return None, []

    def _season_url(self, series_url: str, season_number: int) -> str:
        return f"{series_url}/temporada/{season_number}"

    def _extract_episode_cards(self, series_url: str, season_number: int) -> List[Dict]:
        """Extrae episodios desde la pagina de la serie (selector de temporadas)."""
        episodes = []
        try:
            html_text = self._get_html(series_url, referer=POSEIDON_BASE_URL, timeout=15)
            debug_match = False
            if self.debug_season_url:
                debug_target = self.debug_season_url.rstrip("/")
                series_target = series_url.rstrip("/")
                if debug_target == series_target or debug_target.startswith(f"{series_target}/temporada/"):
                    debug_match = True
            if debug_match:
                self._write_debug_file("season_page.html", html_text)
            if "Just a moment" in html_text or "cf-" in html_text:
                logger.warning(f"Posible bloqueo anti-bot en {series_url}")
            next_data = self._get_next_data(html_text)
            if debug_match:
                has_next = bool(next_data)
                logger.info(f"DEBUG temporada: __NEXT_DATA__={'si' if has_next else 'no'}")
                logger.info(f"DEBUG temporada: len(html)={len(html_text)}")
                if next_data:
                    props = next_data.get("props", {}).get("pageProps", {})
                    logger.info(f"DEBUG temporada: pageProps keys={list(props.keys())}")
                    self._write_debug_file("next_data_season_raw.json", json.dumps(next_data, ensure_ascii=False, indent=2))
            if next_data:
                episodes = self._extract_episodes_from_seasons(next_data, series_url, season_number)
                if not episodes and season_number == 1:
                    season_url = self._season_url(series_url, season_number)
                    episodes = self._extract_episodes_from_next_data(next_data, season_url)
                if episodes:
                    return episodes

            next_json = self._fetch_next_data_json(series_url, html_text=html_text)
            if next_json:
                episodes = self._extract_episodes_from_seasons(next_json, series_url, season_number)
                if not episodes and season_number == 1:
                    season_url = self._season_url(series_url, season_number)
                    episodes = self._extract_episodes_from_next_data(next_json, season_url)
                if episodes:
                    return episodes

            soup = BeautifulSoup(html_text, "html.parser")

            ul = soup.find("ul", class_=re.compile(r"all-episodes"))
            if season_number != 1:
                return episodes

            if not ul:
                if debug_match:
                    logger.info("DEBUG temporada: no se encontro ul.all-episodes")
                return episodes

            items = ul.find_all("li", class_="TPostMv")
            for item in items:
                a = item.find("a", href=True)
                if not a:
                    continue
                href = a.get("href", "")
                ep_url = urljoin(POSEIDON_BASE_URL, href)

                title_elem = item.find("h2", class_="Title")
                title = title_elem.get_text(strip=True) if title_elem else ""

                ep_num = None
                year_span = item.find("span", class_="Year")
                if year_span:
                    match = re.search(r"\dx(\d+)", year_span.get_text(strip=True))
                    if match:
                        ep_num = int(match.group(1))

                if ep_num is None:
                    match = re.search(r"/episodio/(\d+)", ep_url)
                    if match:
                        ep_num = int(match.group(1))

                episodes.append({
                    "url": ep_url,
                    "title": title,
                    "episode": ep_num,
                })

            if episodes:
                return episodes

            # Fallback: buscar URLs de episodios en el HTML crudo
            match = re.search(r"/temporada/(\d+)", season_url)
            season_number = match.group(1) if match else None
            episode_links = re.findall(r"/serie/\d+/[^\s'\"]+/temporada/\d+/episodio/\d+", html_text)
            if episode_links:
                if debug_match:
                    logger.info(f"DEBUG temporada: links episodio encontrados={len(episode_links)}")
                unique = {}
                for href in episode_links:
                    ep_url = urljoin(POSEIDON_BASE_URL, href)
                    ep_match = re.search(r"/episodio/(\d+)", href)
                    ep_num = int(ep_match.group(1)) if ep_match else None
                    if season_number and ep_num:
                        key = (season_number, ep_num)
                    else:
                        key = ep_url
                    if key not in unique:
                        unique[key] = {
                            "url": ep_url,
                            "title": "",
                            "episode": ep_num,
                        }
                episodes = list(unique.values())
                if episodes:
                    return episodes

            logger.warning(f"No se detectaron episodios en {series_url} (temporada {season_number})")

        except Exception as exc:
            logger.error(f"Error extrayendo episodios de {series_url} (temporada {season_number}): {exc}")

        return episodes

    def _extract_player_iframe(self, player_url: str, referer: Optional[str] = None) -> Optional[str]:
        """Extrae el iframe final desde un player poseidon."""
        try:
            html_text = self._get_html(player_url, referer=referer or POSEIDON_BASE_URL, timeout=10)
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", html_text)
            if match:
                return self._normalize_url(match.group(1))
            match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", html_text)
            if match:
                return self._normalize_url(match.group(1))

            # Fallback: buscar un link directo a servidores conocidos
            for host in ["streamwish", "vidhide", "streamtape", "filemoon", "dood", "upstream"]:
                host_match = re.search(rf"https?://[^\s'\"]*{host}[^\s'\"]*", html_text, re.IGNORECASE)
                if host_match:
                    return self._normalize_url(host_match.group(0))
        except Exception as exc:
            logger.debug(f"Error extrayendo iframe de {player_url}: {exc}")
        return None

    def _infer_language(self, text: str) -> str:
        text_low = text.lower()
        if "latino" in text_low:
            return "LAT"
        if "subtitulado" in text_low:
            return "SUB"
        if "ingles" in text_low or "english" in text_low:
            return "EN"
        if "espanol" in text_low or "español" in text_low:
            return "ES"
        return "LAT"

    def _extract_episode_servers(self, episode_url: str) -> List[Dict]:
        """Extrae servidores y links finales de un episodio."""
        servers: List[Dict] = []
        try:
            html_text = self._get_html(episode_url, referer=POSEIDON_BASE_URL, timeout=15)
            if self.debug_episode_url and episode_url.rstrip("/") == self.debug_episode_url.rstrip("/"):
                logger.info(f"DEBUG episodio: len(html)={len(html_text)}")
                logger.info(f"DEBUG episodio: contiene data-tr={('data-tr' in html_text)}")
            if "Just a moment" in html_text or "cf-" in html_text:
                logger.warning(f"Posible bloqueo anti-bot en {episode_url}")
            soup = BeautifulSoup(html_text, "html.parser")

            # Buscar listas de servidores por idioma
            uls = soup.find_all("ul", class_=re.compile(r"sub-tab-lang"))
            for ul in uls:
                lang_text = ""
                # buscar texto de idioma cercano
                for prev in ul.find_all_previous("span"):
                    txt = prev.get_text(" ", strip=True)
                    if any(k in txt.lower() for k in ["latino", "subtitulado", "ingles", "english", "espanol", "español"]):
                        lang_text = txt
                        break
                language = self._infer_language(lang_text)

                for li in ul.find_all("li", attrs={"data-tr": True}):
                    player_url = self._normalize_url(li.get("data-tr"))
                    if not player_url:
                        continue
                    final_url = self._extract_player_iframe(player_url, referer=episode_url) or player_url
                    server_text = li.get_text(" ", strip=True)
                    server_name = ""
                    quality = ""
                    match = re.search(r"\.\s*([^-]+?)\s*-\s*(\w+)", server_text)
                    if match:
                        server_name = match.group(1).strip()
                        quality = match.group(2).strip()

                    if not server_name:
                        parsed = urlparse(final_url)
                        server_name = parsed.netloc.replace("www.", "") if parsed.netloc else ""

                    servers.append({
                        "url": final_url,
                        "name": server_name,
                        "server": server_name,
                        "language": language,
                        "quality": quality,
                    })

            # Fallback si no se encontraron listas por idioma
            if not servers:
                # Fallback 1: buscar data-tr en HTML crudo o strings escapados
                player_urls = re.findall(r"data-tr=\"([^\"]+)\"", html_text)
                if not player_urls:
                    player_urls = re.findall(r"data-tr=\\\"([^\"]+)\\\"", html_text)
                if not player_urls:
                    player_urls = re.findall(r"https?://player\.poseidonhd2\.co/player\.php\?h=[^\s'\"]+", html_text)
                if not player_urls:
                    player_urls = re.findall(r"https?:\\/\\/player\.poseidonhd2\.co/player\.php\?h=[^\\\s'\"]+", html_text)

                if self.debug_episode_url and episode_url.rstrip("/") == self.debug_episode_url.rstrip("/"):
                    logger.info(f"DEBUG episodio: player_urls encontrados={len(player_urls)}")

                seen = set()
                for player_url in player_urls:
                    player_url = self._normalize_url(player_url)
                    if player_url in seen:
                        continue
                    seen.add(player_url)
                    final_url = self._extract_player_iframe(player_url, referer=episode_url) or player_url
                    parsed = urlparse(final_url)
                    server_name = parsed.netloc.replace("www.", "") if parsed.netloc else ""
                    servers.append({
                        "url": final_url,
                        "name": server_name,
                        "server": server_name,
                        "language": "LAT",
                        "quality": "",
                    })

            # Fallback 2: si igual esta vacio, intentar extraer URLs directas
            if not servers:
                direct_urls = re.findall(r"https?://[^\s'\"]+", html_text)
                if not direct_urls:
                    direct_urls = re.findall(r"https?:\\/\\/[^\\\s'\"]+", html_text)
                for url in direct_urls:
                    url = self._normalize_url(url)
                    if any(host in url for host in ["streamwish", "vidhide", "streamtape", "filemoon", "dood", "upstream"]):
                        parsed = urlparse(url)
                        server_name = parsed.netloc.replace("www.", "") if parsed.netloc else ""
                        servers.append({
                            "url": url,
                            "name": server_name,
                            "server": server_name,
                            "language": "LAT",
                            "quality": "",
                        })

            # Fallback 3: si no se encontraron listas por idioma
            if not servers:
                for li in soup.find_all("li", attrs={"data-tr": True}):
                    player_url = self._normalize_url(li.get("data-tr"))
                    if not player_url:
                        continue
                    final_url = self._extract_player_iframe(player_url, referer=episode_url) or player_url
                    parsed = urlparse(final_url)
                    server_name = parsed.netloc.replace("www.", "") if parsed.netloc else ""
                    servers.append({
                        "url": final_url,
                        "name": server_name,
                        "server": server_name,
                        "language": "LAT",
                        "quality": "",
                    })

        except Exception as exc:
            logger.error(f"Error extrayendo servidores de {episode_url}: {exc}")

        return servers

    def _load_existing_series(self, output_file: str = "series.json") -> Dict[int, Dict]:
        """Carga series existentes desde el root del workspace."""
        full_path = os.path.join(self._workspace_root(), output_file)
        if not os.path.exists(full_path):
            return {}
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(s["tmdb_id"]): s for s in data if s.get("tmdb_id")}
        except Exception as exc:
            logger.warning(f"No se pudo cargar series existentes: {exc}")
            return {}

    def _save_series(self, series_map: Dict[int, Dict], output_file: str = "series.json") -> None:
        full_path = os.path.join(self._workspace_root(), output_file)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(list(series_map.values()), f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Guardadas {len(series_map)} series en {full_path}")
        except Exception as exc:
            logger.error(f"Error guardando series: {exc}")

    def _merge_series(self, existing: Dict, new_info: Dict, new_episodes: List[Dict]) -> Dict:
        """Merge de metadata y episodios sin duplicar."""
        merged = dict(existing) if existing else {}
        for key, value in new_info.items():
            if key not in merged or merged.get(key) in (None, "", 0, []):
                merged[key] = value

        if "created_at" not in merged or not merged.get("created_at"):
            merged["created_at"] = datetime.now(timezone.utc).isoformat()

        existing_eps = {(e.get("season"), e.get("episode")) for e in merged.get("episodios", [])}
        merged.setdefault("episodios", [])
        for ep in new_episodes:
            key = (ep.get("season"), ep.get("episode"))
            if key not in existing_eps:
                merged["episodios"].append(ep)

        merged["number_of_episodes"] = len(merged.get("episodios", []))
        return merged

    def run(self, max_pages: Optional[int] = None, max_series: Optional[int] = None, max_episodes: Optional[int] = None):
        logger.info("Iniciando scraper de series Poseidon...")
        series_map = self._load_existing_series()

        current_url = SERIES_URL
        page = 1
        processed = 0

        while current_url:
            if max_pages and page > max_pages:
                break

            logger.info(f"Procesando grid {page}: {current_url}")
            items, next_url = self._extract_grid_series(current_url)
            if not items:
                break

            for item in items:
                if max_series and processed >= max_series:
                    break

                series_url = item.get("url")
                tmdb_id = self._extract_tmdb_id_from_url(series_url)
                if not series_url or not tmdb_id:
                    continue

                if tmdb_id in self.processed_series_ids:
                    continue

                logger.info(f"Serie: {item.get('title') or series_url}")
                info, seasons = self._parse_series_info(series_url)
                if not info:
                    continue

                existing = series_map.get(tmdb_id)
                existing_eps = {(e.get("season"), e.get("episode")) for e in existing.get("episodios", [])} if existing else set()

                new_episodes: List[Dict] = []
                for season_number in seasons:
                    if season_number == 0:
                        continue
                    episode_cards = self._extract_episode_cards(series_url, season_number)

                    for ep in episode_cards:
                        ep_num = ep.get("episode")
                        if max_episodes and len(new_episodes) >= max_episodes:
                            break
                        if (season_number, ep_num) in existing_eps:
                            continue

                        servers = self._extract_episode_servers(ep.get("url"))
                        new_episodes.append({
                            "season": season_number,
                            "episode": ep_num,
                            "title": ep.get("title") or f"Episodio {ep_num}",
                            "servidores": servers,
                        })
                        time.sleep(0.5)

                    if max_episodes and len(new_episodes) >= max_episodes:
                        break

                series_map[tmdb_id] = self._merge_series(existing, info, new_episodes)
                self.processed_series_ids.add(tmdb_id)
                processed += 1

                logger.info(f"✅ Serie actualizada: {info.get('name')} (nuevos episodios: {len(new_episodes)})")
                time.sleep(1)

            if max_series and processed >= max_series:
                break

            current_url = next_url
            page += 1

        self._save_series(series_map)
        logger.info("Scraping completado.")

    def run_single(self, series_url: str, max_episodes: Optional[int] = None):
        """Procesa una unica serie dada su URL absoluta o relativa."""
        if not series_url:
            logger.error("No se proporciono URL de serie")
            return

        if series_url.startswith("/"):
            series_url = urljoin(POSEIDON_BASE_URL, series_url)

        tmdb_id = self._extract_tmdb_id_from_url(series_url)
        if not tmdb_id:
            logger.error("No se pudo extraer TMDB ID de la URL: %s", series_url)
            return

        series_map = self._load_existing_series()

        logger.info("Procesando serie unica: %s", series_url)
        info, seasons = self._parse_series_info(series_url)
        if not info:
            logger.error("No se pudo obtener informacion de la serie")
            return

        existing = series_map.get(tmdb_id)
        existing_eps = {(e.get("season"), e.get("episode")) for e in existing.get("episodios", [])} if existing else set()

        new_episodes: List[Dict] = []
        for season_number in seasons:
            if season_number == 0:
                continue
            episode_cards = self._extract_episode_cards(series_url, season_number)
            for ep in episode_cards:
                ep_num = ep.get("episode")
                if max_episodes and len(new_episodes) >= max_episodes:
                    break
                if (season_number, ep_num) in existing_eps:
                    continue

                servers = self._extract_episode_servers(ep.get("url"))
                new_episodes.append({
                    "season": season_number,
                    "episode": ep_num,
                    "title": ep.get("title") or f"Episodio {ep_num}",
                    "servidores": servers,
                })
                time.sleep(0.5)

            if max_episodes and len(new_episodes) >= max_episodes:
                break

        series_map[tmdb_id] = self._merge_series(existing, info, new_episodes)
        self._save_series(series_map)
        logger.info("✅ Serie unica procesada: %s (nuevos episodios: %d)", info.get("name"), len(new_episodes))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scraper de series desde poseidonhd2.co")
    parser.add_argument("--max-pages", type=int, default=None, help="Numero maximo de paginas")
    parser.add_argument("--max-series", type=int, default=None, help="Numero maximo de series")
    parser.add_argument("--max-episodes", type=int, default=None, help="Numero maximo de episodios por corrida")
    parser.add_argument("--series-url", type=str, default=None, help="URL de una serie especifica a procesar (ej: https://www.poseidonhd2.co/serie/44006/chicago-fire)")
    parser.add_argument("--debug-season-url", type=str, default=None, help="URL de temporada para debug")
    parser.add_argument("--debug-episode-url", type=str, default=None, help="URL de episodio para debug")

    args = parser.parse_args()

    scraper = PoseidonSeriesScraper()
    scraper.debug_season_url = args.debug_season_url
    scraper.debug_episode_url = args.debug_episode_url
    if args.series_url:
        scraper.run_single(args.series_url, max_episodes=args.max_episodes)
    else:
        scraper.run(max_pages=args.max_pages, max_series=args.max_series, max_episodes=args.max_episodes)


if __name__ == "__main__":
    main()
