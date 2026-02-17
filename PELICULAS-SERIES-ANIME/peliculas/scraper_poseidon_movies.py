"""
Scraper de peliculas desde poseidonhd2.co/peliculas
Navega por grids, abre cada pelicula y extrae servidores.
Guarda y actualiza peliculas.json en el root del workspace.
"""

import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Agregar el directorio padre al path para importar el extractor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from scraper_embed_extractor import extract_from_embed
    M3U8_EXTRACTOR_AVAILABLE = True
except ImportError:
    M3U8_EXTRACTOR_AVAILABLE = False
    print("AVISO: scraper_embed_extractor no disponible, no se extraerán URLs m3u8")

POSEIDON_BASE_URL = "https://www.poseidonhd2.co"
MOVIES_URL = f"{POSEIDON_BASE_URL}/peliculas"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PoseidonMoviesScraper:
    def __init__(self, extract_m3u8: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.processed_movie_ids = set()
        self.extract_m3u8 = extract_m3u8 and M3U8_EXTRACTOR_AVAILABLE

    def _workspace_root(self) -> str:
        """Devuelve la ruta base del workspace (dos niveles arriba)."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(script_dir, "..", ".."))

    def _get_next_data(self, html_text: str) -> Optional[Dict]:
        """Extrae el JSON de __NEXT_DATA__."""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if script:
                content = script.string if script.string else script.get_text(strip=False)
                if content:
                    return json.loads(content)
        except Exception as exc:
            logger.debug(f"Error parseando __NEXT_DATA__: {exc}")
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

    def _extract_tmdb_id_from_url(self, movie_url: str) -> Optional[int]:
        match = re.search(r"/pelicula/(\d+)/", movie_url)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
        return None

    def _extract_grid_movies(self, page_url: str) -> Tuple[List[Dict], Optional[str]]:
        """Extrae URLs de peliculas desde un grid y devuelve next page si existe."""
        results = []
        next_url = None
        try:
            response = self.session.get(page_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

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
                movie_url = urljoin(POSEIDON_BASE_URL, href)
                results.append({
                    "url": movie_url,
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

    def _parse_movie_info(self, movie_url: str) -> Optional[Dict]:
        """Extrae informacion de la pelicula."""
        try:
            response = self.session.get(movie_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            title = ""
            overview = ""
            genres: List[str] = []
            poster_url = ""
            backdrop_url = ""
            rating = 0.0
            year = ""

            next_data = self._get_next_data(response.text)
            if next_data:
                movie_data = self._find_dict_with_keys(next_data, ["TMDbId", "titles", "overview"])
                if movie_data:
                    title = movie_data.get("titles", {}).get("name", "")
                    overview = movie_data.get("overview", "")
                    release_date = movie_data.get("releaseDate", "")
                    if release_date:
                        year = release_date.split("-")[0]
                    rating = movie_data.get("rate", {}).get("average", 0) or 0
                    genres = [g.get("name", "") for g in movie_data.get("genres", []) if g.get("name")]
                    poster_url = movie_data.get("images", {}).get("poster", "")
                    backdrop_url = movie_data.get("images", {}).get("backdrop", "")

            if not title:
                title_elem = soup.find("h1", class_="Title")
                title = title_elem.get_text(strip=True) if title_elem else ""

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

            if not rating:
                vote_elem = soup.find("div", id="TPVotes")
                if vote_elem and vote_elem.get("data-percent"):
                    try:
                        rating = float(vote_elem.get("data-percent")) / 10.0
                    except Exception:
                        rating = 0.0

            if not year:
                meta = soup.find("p", class_="meta")
                if meta:
                    spans = meta.find_all("span")
                    if spans:
                        year = spans[-1].get_text(strip=True)

            tmdb_id = self._extract_tmdb_id_from_url(movie_url)
            if not tmdb_id:
                return None

            return {
                "tmdb_id": tmdb_id,
                "title": title,
                "year": year,
                "servers": [],
                "poster_url": poster_url,
                "backdrop_url": backdrop_url,
                "genres_spanish": genres,
                "overview": overview,
                "rating": rating,
            }
        except Exception as exc:
            logger.error(f"Error extrayendo info de pelicula {movie_url}: {exc}")
            return None

    def _extract_player_iframe(self, player_url: str) -> Optional[str]:
        """Extrae el iframe final desde un player poseidon."""
        try:
            response = self.session.get(player_url, timeout=10)
            response.encoding = "utf-8"
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", response.text)
            if match:
                return match.group(1)
        except Exception as exc:
            logger.debug(f"Error extrayendo iframe de {player_url}: {exc}")
        return None

    def _infer_language(self, text: str) -> str:
        text_low = text.lower()
        if "latino" in text_low:
            return "LATINO"
        if "subtitulado" in text_low:
            return "SUB"
        if "ingles" in text_low or "english" in text_low:
            return "ENGLISH"
        if "espanol" in text_low or "español" in text_low:
            return "ESPANOL"
        return "LATINO"

    def _is_doodstream(self, value: str) -> bool:
        return "doodstream" in value.lower()

    def _extract_m3u8_for_server(self, embed_url: str) -> Optional[str]:
        """Extrae la URL m3u8 de un embed usando el extractor."""
        if not self.extract_m3u8 or not embed_url:
            return None
        try:
            result = extract_from_embed(embed_url)
            if result and result.get('best_url'):
                logger.debug(f"M3U8 extraído: {result['best_url'][:60]}...")
                return result['best_url']
            else:
                error = result.get('error', 'Sin URL') if result else 'Sin resultado'
                logger.debug(f"No se pudo extraer m3u8 de {embed_url}: {error}")
        except Exception as exc:
            logger.debug(f"Error extrayendo m3u8 de {embed_url}: {exc}")
        return None

    def _extract_movie_servers(self, movie_url: str) -> List[Dict]:
        """Extrae servidores y links finales de una pelicula."""
        servers: List[Dict] = []
        try:
            response = self.session.get(movie_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            uls = soup.find_all("ul", class_=re.compile(r"sub-tab-lang"))
            for ul in uls:
                lang_text = ""
                for prev in ul.find_all_previous("span"):
                    txt = prev.get_text(" ", strip=True)
                    if any(k in txt.lower() for k in ["latino", "subtitulado", "ingles", "english", "espanol", "español"]):
                        lang_text = txt
                        break
                language = self._infer_language(lang_text)

                for li in ul.find_all("li", attrs={"data-tr": True}):
                    player_url = li.get("data-tr")
                    if not player_url or self._is_doodstream(player_url):
                        continue

                    final_url = self._extract_player_iframe(player_url) or player_url
                    if self._is_doodstream(final_url):
                        continue

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

                    if self._is_doodstream(server_name):
                        continue

                    server_entry = {
                        "server": server_name,
                        "quality": quality or "HD",
                        "language": language,
                        "embed_url": final_url,
                    }
                    # Extraer m3u8 si está habilitado
                    if self.extract_m3u8:
                        m3u8_result = self._extract_m3u8_for_server(final_url)
                        if m3u8_result:
                            server_entry["m3u8_url"] = m3u8_result
                    servers.append(server_entry)

            if not servers:
                for li in soup.find_all("li", attrs={"data-tr": True}):
                    player_url = li.get("data-tr")
                    if not player_url or self._is_doodstream(player_url):
                        continue
                    final_url = self._extract_player_iframe(player_url) or player_url
                    if self._is_doodstream(final_url):
                        continue
                    parsed = urlparse(final_url)
                    server_name = parsed.netloc.replace("www.", "") if parsed.netloc else ""
                    if self._is_doodstream(server_name):
                        continue
                    server_entry = {
                        "server": server_name,
                        "quality": "HD",
                        "language": "LATINO",
                        "embed_url": final_url,
                    }
                    # Extraer m3u8 si está habilitado
                    if self.extract_m3u8:
                        m3u8_result = self._extract_m3u8_for_server(final_url)
                        if m3u8_result:
                            server_entry["m3u8_url"] = m3u8_result
                    servers.append(server_entry)

        except Exception as exc:
            logger.error(f"Error extrayendo servidores de {movie_url}: {exc}")

        return servers

    def _load_existing_movies(self, output_file: str = "peliculas.json") -> Dict[int, Dict]:
        """Carga peliculas existentes desde el root del workspace."""
        full_path = os.path.join(self._workspace_root(), output_file)
        if not os.path.exists(full_path):
            return {}
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(m["tmdb_id"]): m for m in data if m.get("tmdb_id")}
        except Exception as exc:
            logger.warning(f"No se pudo cargar peliculas existentes: {exc}")
            return {}

    def _save_movies(self, movies_map: Dict[int, Dict], output_file: str = "peliculas.json") -> None:
        full_path = os.path.join(self._workspace_root(), output_file)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(list(movies_map.values()), f, indent=2, ensure_ascii=False)
            logger.info(f"Guardadas {len(movies_map)} peliculas en {full_path}")
        except Exception as exc:
            logger.error(f"Error guardando peliculas: {exc}")

    def _merge_movie(self, existing: Optional[Dict], new_info: Dict, new_servers: List[Dict]) -> Dict:
        merged = dict(existing) if existing else {}
        for key, value in new_info.items():
            if key not in merged or merged.get(key) in (None, "", 0, []):
                merged[key] = value

        merged["servers"] = self._normalize_servers(merged.get("servers"))
        
        # Crear índice de servidores existentes por clave (server, language, embed_url)
        existing_servers_map = {}
        for i, s in enumerate(merged["servers"]):
            key = (s.get("server"), s.get("language"), s.get("embed_url"))
            existing_servers_map[key] = i
        
        for server in new_servers:
            key = (server.get("server"), server.get("language"), server.get("embed_url"))
            if key in existing_servers_map:
                # Servidor ya existe - actualizar con m3u8_url si el nuevo lo tiene
                idx = existing_servers_map[key]
                if server.get("m3u8_url") and not merged["servers"][idx].get("m3u8_url"):
                    merged["servers"][idx]["m3u8_url"] = server["m3u8_url"]
            else:
                # Servidor nuevo - agregar
                merged["servers"].append(server)

        return self._normalize_movie_record(merged)

    def _normalize_movie_record(self, record: Dict) -> Dict:
        """Normaliza la estructura del registro de pelicula."""
        normalized = dict(record) if record else {}

        normalized["tmdb_id"] = normalized.get("tmdb_id")
        normalized["title"] = normalized.get("title", "")
        normalized["year"] = normalized.get("year", "")
        normalized["servers"] = self._normalize_servers(normalized.get("servers"))
        normalized["poster_url"] = normalized.get("poster_url", "")
        normalized["backdrop_url"] = normalized.get("backdrop_url", "")
        normalized["genres_spanish"] = normalized.get("genres_spanish", []) or []
        normalized["overview"] = normalized.get("overview", "")
        normalized["rating"] = normalized.get("rating", 0) or 0

        return normalized

    def _normalize_servers(self, servers) -> List[Dict]:
        """Normaliza servidores existentes a lista de dicts."""
        if servers is None:
            return []
        if isinstance(servers, str):
            try:
                servers = json.loads(servers)
            except Exception:
                return []
        if not isinstance(servers, list):
            return []

        normalized: List[Dict] = []
        for item in servers:
            if isinstance(item, dict):
                normalized.append(item)
                continue
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    normalized.append(parsed)
                elif isinstance(parsed, list):
                    normalized.extend([p for p in parsed if isinstance(p, dict)])
        return normalized

    def _is_single_movie_url(self, url: str) -> bool:
        """Verifica si la URL es de una película individual."""
        return "/pelicula/" in url

    def _process_single_movie(self, movie_url: str, movies_map: Dict[int, Dict]) -> int:
        """Procesa una sola película y retorna 1 si fue exitoso, 0 si no."""
        tmdb_id = self._extract_tmdb_id_from_url(movie_url)
        if not tmdb_id:
            logger.error(f"No se pudo extraer TMDB ID de {movie_url}")
            return 0

        logger.info(f"Procesando película: {movie_url}")
        info = self._parse_movie_info(movie_url)
        if not info:
            logger.error(f"No se pudo obtener info de {movie_url}")
            return 0

        servers = self._extract_movie_servers(movie_url)
        existing = movies_map.get(tmdb_id)
        movies_map[tmdb_id] = self._merge_movie(existing, info, servers)
        self.processed_movie_ids.add(tmdb_id)

        logger.info(f"Actualizada: {info.get('title')} (servers: {len(servers)})")
        return 1

    def run(self, max_pages: Optional[int] = None, max_movies: Optional[int] = None, custom_url: Optional[str] = None):
        logger.info("Iniciando scraper de peliculas Poseidon...")
        if self.extract_m3u8:
            logger.info("Extracción de URLs m3u8 HABILITADA")
        else:
            logger.info("Extracción de URLs m3u8 DESHABILITADA")
        movies_map = self._load_existing_movies()

        # Determinar URL inicial
        if custom_url:
            # Normalizar URL
            if not custom_url.startswith("http"):
                start_url = urljoin(POSEIDON_BASE_URL, custom_url)
            else:
                start_url = custom_url
            
            # Si es una película individual, procesarla directamente
            if self._is_single_movie_url(start_url):
                logger.info(f"Procesando película individual: {start_url}")
                processed = self._process_single_movie(start_url, movies_map)
                self._save_movies(movies_map)
                logger.info(f"Scraping completado. Películas procesadas: {processed}")
                return
            else:
                logger.info(f"Procesando lista/grid desde: {start_url}")
        else:
            start_url = MOVIES_URL

        current_url = start_url
        page = 1
        processed = 0

        while current_url:
            if max_pages and page > max_pages:
                break

            logger.info(f"Procesando grid {page}: {current_url}")
            items, next_url = self._extract_grid_movies(current_url)
            if not items:
                break

            for item in items:
                if max_movies and processed >= max_movies:
                    break

                movie_url = item.get("url")
                tmdb_id = self._extract_tmdb_id_from_url(movie_url) if movie_url else None
                if not movie_url or not tmdb_id:
                    continue

                if tmdb_id in self.processed_movie_ids:
                    continue

                logger.info(f"Pelicula: {item.get('title') or movie_url}")
                info = self._parse_movie_info(movie_url)
                if not info:
                    continue

                servers = self._extract_movie_servers(movie_url)
                existing = movies_map.get(tmdb_id)
                movies_map[tmdb_id] = self._merge_movie(existing, info, servers)
                self.processed_movie_ids.add(tmdb_id)
                processed += 1

                logger.info(f"Actualizada: {info.get('title')} (servers: {len(servers)})")
                time.sleep(1)

            if max_movies and processed >= max_movies:
                break

            current_url = next_url
            page += 1

        self._save_movies(movies_map)
        logger.info("Scraping completado.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scraper de peliculas desde poseidonhd2.co")
    parser.add_argument("--max-pages", type=int, default=None, help="Numero maximo de paginas")
    parser.add_argument("--max-movies", type=int, default=None, help="Numero maximo de peliculas")
    parser.add_argument("--url", type=str, default=None, help="""URL personalizada para extraer. Ejemplos:
        - Lista/tendencias: https://www.poseidonhd2.co/peliculas/tendencias/semana
        - Por genero: https://www.poseidonhd2.co/genero/accion
        - Pelicula directa: https://www.poseidonhd2.co/pelicula/338969/the-toxic-avenger""")
    parser.add_argument("--no-m3u8", action="store_true", help="No extraer URLs m3u8 de los embeds")

    args = parser.parse_args()

    scraper = PoseidonMoviesScraper(extract_m3u8=not args.no_m3u8)
    scraper.run(max_pages=args.max_pages, max_movies=args.max_movies, custom_url=args.url)


if __name__ == "__main__":
    main()
