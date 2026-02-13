"""
Scraper de animes desde ww1.henaojara.net
Extrae: series, temporadas, episodios, servidores disponibles
Guarda estructura: {tmdb_id, title, year, seasons[episodes[servers]]}
"""

import json
import time
import logging
import os
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración
BASE_URL = "https://ww1.henaojara.net"
GRID_URL = f"{BASE_URL}/animes?tipo=anime"

# TMDB
TMDB_API_KEY = "201d333198374a91c81dba3c443b1a8e"
TMDB_BASE_URL = "https://api.themoviedb.org/3"


class HenaojaraAnimeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.animes = []          # anime2.json (destino)
        self.legacy_animes = []   # anime.json (solo lectura + borrado)
        self.legacy_modified = False
        self.processed_tmdb_ids = set()
        self.visited_anime_urls = set()

    def _workspace_root(self) -> str:
        """Devuelve la ruta base del workspace (dos niveles arriba)."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(script_dir, "..", ".."))

    def _clean_base_title(self, title: str) -> Tuple[str, int]:
        """Quita sufijos de temporada y devuelve (base_title, season_number)."""
        season_number = 1
        base = title.strip()

        patterns = [
            r"\b(\d+)(st|nd|rd|th)\s+Season\b",
            r"\bSeason\s+(\d+)\b",
            r"\bTemporada\s+(\d+)\b",
            r"\b(\d+)(ra|da|ta|na)\s+Temporada\b",
            r"\bS(\d+)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, base, re.IGNORECASE)
            if match:
                try:
                    season_number = int(match.group(1))
                except Exception:
                    season_number = 1
                base = re.sub(pattern, "", base, flags=re.IGNORECASE).strip()
                break

        base = re.sub(r"\s{2,}", " ", base).strip()
        return base, season_number

    def _normalize_slug(self, slug: str) -> str:
        """Normaliza slug de temporada a slug base si aplica."""
        slug = slug.strip("/")
        slug = re.sub(r"-(\d+)(st|nd|rd|th)-season$", "", slug)
        slug = re.sub(r"-season-(\d+)$", "", slug)
        slug = re.sub(r"-(\d+)(ra|da|ta|na)-temporada$", "", slug)
        return slug

    def _extract_episode_number(self, text: str, href: str) -> Optional[int]:
        if text:
            match = re.search(r"Episodio\s+(\d+)", text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        if href:
            clean = href.rstrip("/")
            match = re.search(r"-(\d+)$", clean)
            if match:
                return int(match.group(1))
        return None

    def _get_slug_from_url(self, anime_url: str) -> str:
        try:
            path = urlparse(anime_url).path.strip("/")
            parts = path.split("/")
            if parts and parts[0] == "anime" and len(parts) > 1:
                return parts[1]
        except Exception:
            pass
        return ""

    def _decode_hex_url(self, hex_str: str) -> Optional[str]:
        try:
            hex_str = hex_str.strip()
            if len(hex_str) % 2 != 0:
                return None
            return bytes.fromhex(hex_str).decode("utf-8")
        except Exception:
            return None

    def buscar_tmdb(self, title: str) -> Optional[Dict]:
        """Busca anime en TMDB (TV)."""
        try:
            params = {
                "api_key": TMDB_API_KEY,
                "query": title,
                "language": "es-ES",
                "page": 1
            }
            response = self.session.get(f"{TMDB_BASE_URL}/search/tv", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                logger.warning(f"No se encontró en TMDB: {title}")
                return None

            best = results[0]
            return {
                "tmdb_id": best.get("id"),
                "title": best.get("name"),
                "year": best.get("first_air_date", "").split("-")[0] if best.get("first_air_date") else "",
                "overview": best.get("overview", ""),
                "rating": best.get("vote_average", 0),
                "genres": []
            }
        except Exception as e:
            logger.error(f"Error buscando en TMDB '{title}': {e}")
            return None

    def extraer_grid(self, page_url: str) -> List[Dict]:
        """Extrae animes desde el grid."""
        animes = []
        try:
            response = self.session.get(page_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            section = soup.find("section", class_="cn")
            if not section:
                logger.warning("No se encontró section.cn")
                return animes

            grid = section.find("div", class_="ul")
            if not grid:
                logger.warning("No se encontró div.ul dentro de section.cn")
                return animes

            items = grid.find_all("article", class_="li")
            logger.info(f"Se encontraron {len(items)} animes en la página")

            for item in items:
                a = item.find("a", href=True)
                h3 = item.find("h3", class_="h")
                title_a = h3.find("a") if h3 else None
                if a and title_a:
                    url = urljoin(BASE_URL, a["href"])
                    title = title_a.get_text(strip=True)
                    animes.append({"url": url, "title": title})

        except Exception as e:
            logger.error(f"Error extrayendo grid de {page_url}: {e}")

        return animes

    def extraer_info_anime(self, anime_url: str) -> Optional[Dict]:
        """Extrae la información de un anime desde su página."""
        try:
            response = self.session.get(anime_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            info = soup.find("div", class_="info")
            if not info:
                logger.warning(f"No se encontró div.info en {anime_url}")
                return None

            title_elem = info.find("h1")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            base_title, season_number = self._clean_base_title(title)

            status_elem = info.find("span", class_="e")
            status = status_elem.get_text(strip=True) if status_elem else ""

            synopsis_elem = info.find("div", class_="tx")
            synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else ""

            genres = []
            genres_ul = info.find("ul", class_="gn")
            if genres_ul:
                for li in genres_ul.find_all("li"):
                    g = li.get_text(strip=True)
                    if g:
                        genres.append(g)

            # Buscar conteo de episodios si existe
            episodes_total = ""
            dt_ul = info.find("ul", class_="dt")
            if dt_ul:
                for li in dt_ul.find_all("li"):
                    text = li.get_text(strip=True)
                    if text.lower().startswith("episodios"):
                        episodes_total = text.split(":", 1)[-1].strip()

            # Buscar TMDB
            tmdb_info = self.buscar_tmdb(base_title)

            raw_slug = self._get_slug_from_url(anime_url)
            base_slug = self._normalize_slug(raw_slug) if raw_slug else ""
            base_url = f"{BASE_URL}/anime/{base_slug}" if base_slug else anime_url

            return {
                "title": base_title,
                "original_title": title,
                "season_number": season_number,
                "status": status,
                "overview": tmdb_info.get("overview", synopsis) if tmdb_info else synopsis,
                "rating": tmdb_info.get("rating", 0) if tmdb_info else 0,
                "genres": tmdb_info.get("genres", genres) if tmdb_info else genres,
                "tmdb_id": tmdb_info.get("tmdb_id") if tmdb_info else None,
                "year": tmdb_info.get("year", "") if tmdb_info else "",
                "episodes_total": episodes_total,
                "url": anime_url,
                "base_url": base_url,
                "raw_slug": raw_slug
            }

        except Exception as e:
            logger.error(f"Error extrayendo info de {anime_url}: {e}")
            return None

    def extraer_episodios(self, anime_url: str) -> List[Dict]:
        """Extrae la lista de episodios de una serie."""
        episodios = []
        try:
            response = self.session.get(anime_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            eplist = soup.find("ul", class_="eplist")
            found_from_list = False
            if not eplist:
                logger.warning(f"No se encontró ul.eplist en {anime_url}")
            else:
                for li in eplist.find_all("li"):
                    a = li.find("a", href=True)
                    if not a:
                        continue
                    ep_url = urljoin(BASE_URL, a["href"])
                    span = a.find("span")
                    text = span.get_text(" ", strip=True) if span else a.get_text(" ", strip=True)
                    ep_number = self._extract_episode_number(text, ep_url)
                    episodios.append({"url": ep_url, "number": ep_number})
                found_from_list = len(episodios) > 0

            # Fallback: buscar cualquier link /ver/ si no se encontraron episodios
            if not episodios:
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    if "/ver/" in href:
                        ep_url = urljoin(BASE_URL, href)
                        text = a.get_text(" ", strip=True)
                        ep_number = self._extract_episode_number(text, ep_url)
                        episodios.append({"url": ep_url, "number": ep_number})

            # Fallback 2: parsear script var eps y data-sl
            if not episodios:
                slug = None
                th = soup.find("div", class_="th", attrs={"data-sl": True})
                if th:
                    slug = th.get("data-sl")
                if not slug:
                    slug = self._get_slug_from_url(anime_url)

                scripts = soup.find_all("script")
                for script in scripts:
                    content = script.string if script.string else script.get_text(strip=False)
                    if content and "var eps" in content:
                        match = re.search(r"var\s+eps\s*=\s*(\[\[.*?\]\]);", content, re.DOTALL)
                        if match:
                            eps_raw = match.group(1)
                            try:
                                eps_list = json.loads(eps_raw)
                                for item in eps_list:
                                    if isinstance(item, list) and item:
                                        ep_num = item[0]
                                        ep_url = f"{BASE_URL}/ver/{slug}-{ep_num}" if slug else anime_url
                                        episodios.append({"url": ep_url, "number": int(ep_num)})
                            except Exception:
                                pass
                        break

            # Eliminar duplicados por URL
            unique = {}
            for ep in episodios:
                unique[ep["url"]] = ep
            episodios = list(unique.values())

            if not episodios:
                logger.warning(f"No se detectaron episodios en {anime_url}")

        except Exception as e:
            logger.error(f"Error extrayendo episodios de {anime_url}: {e}")

        return episodios

    def extraer_servidores_episodio(self, episode_url: str) -> List[Dict]:
        """Extrae servidores del episodio mediante petición AJAX."""
        servers = []
        seen = set()
        try:
            # Primero visitar la página del episodio para obtener cookies
            response = self.session.get(episode_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # Buscar data-encrypt en ul.opt
            opt_ul = soup.find("ul", class_="opt")
            if not opt_ul or not opt_ul.get("data-encrypt"):
                logger.warning(f"No se encontró ul.opt[data-encrypt] en {episode_url}")
                return servers

            data_encrypt = opt_ul.get("data-encrypt")
            
            # Hacer petición AJAX a /hj para obtener los servidores
            ajax_url = urljoin(BASE_URL, "hj")
            ajax_data = {
                "acc": "opt",
                "i": data_encrypt
            }
            
            # Headers AJAX necesarios
            ajax_headers = {
                "Referer": episode_url,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            ajax_response = self.session.post(ajax_url, data=ajax_data, headers=ajax_headers, timeout=15)
            ajax_response.encoding = "utf-8"
            
            if not ajax_response.text.strip():
                logger.warning(f"AJAX retornó respuesta vacía para {episode_url}")
                return servers
            
            # Parsear respuesta HTML con los servidores
            ajax_soup = BeautifulSoup(ajax_response.text, "html.parser")
            
            # Extraer cada servidor <li encrypt="...">
            for li in ajax_soup.find_all("li", attrs={"encrypt": True}):
                encrypt_hex = li.get("encrypt")
                if encrypt_hex:
                    decoded_url = self._decode_hex_url(encrypt_hex)
                    if decoded_url:
                        parsed = urlparse(decoded_url)
                        server_name = parsed.netloc.replace("www.", "")
                        key = f"{server_name}|{decoded_url}"
                        if key not in seen:
                            servers.append({"url": decoded_url, "server": server_name})
                            seen.add(key)

            logger.info(f"✓ {len(servers)} servidores extraídos de {episode_url.split('/')[-1]}")

        except Exception as e:
            logger.error(f"Error extrayendo servidores de {episode_url}: {e}")

        return servers

    def _necesita_actualizacion(self, anime_url: str, tmdb_id: int, season_number: int, nuevos_episodios: List[Dict]) -> bool:
        """Verifica si un anime necesita actualización."""
        if not tmdb_id:
            return True
        
        # Buscar en animes ya cargados
        existing = next((s for s in self.animes if s.get("tmdb_id") == tmdb_id), None)
        if not existing:
            return True
        
        # Buscar temporada
        season = next((s for s in existing.get("seasons", []) if s.get("number") == season_number), None)
        if not season:
            return True
        
        # Comparar números de episodios
        existing_eps = {e.get("number") for e in season.get("episodes", [])}
        nuevos_eps = {ep.get("number") for ep in nuevos_episodios}
        episodios_faltantes = nuevos_eps - existing_eps
        
        if episodios_faltantes:
            logger.info(f"🔄 Faltan {len(episodios_faltantes)} episodios para temporada {season_number}")
            return True
        
        logger.info(f"⏭️ Ya está completo, saltando...")
        return False

    def procesar_animes(self, max_animes: int = None, max_pages: int = None):
        """Procesa múltiples animes desde las páginas solicitadas."""
        all_animes = []
        page = 1

        if max_pages:
            logger.info(f"Procesando hasta {max_pages} páginas...")
        else:
            logger.info("Detectando páginas disponibles...")

        while True:
            if max_pages and page > max_pages:
                logger.info(f"✓ Total de páginas procesadas: {page - 1}")
                break
            page_url = f"{GRID_URL}&pag={page}" if page > 1 else GRID_URL
            animes_page = self.extraer_grid(page_url)
            
            if not animes_page:
                logger.info(f"✓ Total de páginas encontradas: {page - 1}")
                break
            
            all_animes.extend(animes_page)
            logger.info(f"  Página {page}: {len(animes_page)} animes")
            page += 1
            time.sleep(0.5)
        
        logger.info(f"✓ Total de animes encontrados: {len(all_animes)}")
        
        # Limitar si se especificó max_animes
        animes_a_procesar = all_animes[:max_animes] if max_animes else all_animes
        
        for idx, anime in enumerate(animes_a_procesar):
            try:
                if anime["url"] in self.visited_anime_urls:
                    continue
                self.visited_anime_urls.add(anime["url"])

                logger.info(f"\n--- Anime {idx + 1}/{len(animes_a_procesar)}: {anime.get('title')} ---")
                info = self.extraer_info_anime(anime["url"])
                if not info:
                    continue

                tmdb_id = info.get("tmdb_id")
                base_title = info.get("title")
                season_number = info.get("season_number", 1)
                base_url = info.get("base_url")

                # Extraer lista de episodios (sin servidores aún)
                episodios = self.extraer_episodios(anime["url"])
                
                # Verificar si necesita actualización
                if not self._necesita_actualizacion(anime["url"], tmdb_id, season_number, episodios):
                    continue
                
                # Solo ahora extraer servidores de episodios faltantes
                existing = next((s for s in self.animes if s.get("tmdb_id") == tmdb_id), None)
                if existing:
                    season = next((s for s in existing.get("seasons", []) if s.get("number") == season_number), None)
                    existing_eps = {e.get("number") for e in season.get("episodes", [])} if season else set()
                else:
                    existing_eps = set()
                
                episodes_data = []
                for ep in episodios:
                    ep_number = ep.get("number")
                    if ep_number in existing_eps:
                        continue  # Saltar episodios que ya existen
                    
                    servers = self.extraer_servidores_episodio(ep["url"])
                    title = f"{base_title} Episodio {ep_number}" if ep_number else base_title
                    episodes_data.append({
                        "title": title,
                        "number": ep_number,
                        "servers": servers
                    })
                    time.sleep(0.5)

                # Si es temporada >1 y existe base_url distinto, intentar traer episodios de temporada 1
                if base_url and base_url != anime["url"] and base_url not in self.visited_anime_urls:
                    self.visited_anime_urls.add(base_url)
                    base_episodios = self.extraer_episodios(base_url)
                    base_episodes_data = []
                    for ep in base_episodios:
                        servers = self.extraer_servidores_episodio(ep["url"])
                        number = ep.get("number")
                        title = f"{base_title} Episodio {number}" if number else base_title
                        base_episodes_data.append({
                            "title": title,
                            "number": number,
                            "servers": servers
                        })
                        time.sleep(0.5)
                else:
                    base_episodes_data = []

                # Buscar existente por TMDB
                existing = None
                if tmdb_id:
                    for s in self.animes:
                        if s.get("tmdb_id") == tmdb_id:
                            existing = s
                            break

                if not existing:
                    serie = {
                        "tmdb_id": tmdb_id,
                        "title": base_title,
                        "year": info.get("year", ""),
                        "overview": info.get("overview", ""),
                        "rating": info.get("rating", 0),
                        "genres": info.get("genres", []),
                        "seasons": []
                    }
                    self.animes.append(serie)
                    existing = serie

                # Agregar temporada
                seasons = existing.get("seasons", [])
                season_obj = next((s for s in seasons if s.get("number") == season_number), None)
                if not season_obj:
                    season_obj = {"number": season_number, "episodes": []}
                    seasons.append(season_obj)
                    existing["seasons"] = seasons

                # Agregar episodios sin duplicar
                existing_eps = {e.get("number") for e in season_obj["episodes"]}
                for ep in episodes_data:
                    if ep.get("number") not in existing_eps:
                        season_obj["episodes"].append(ep)

                # Agregar temporada 1 desde base_url si corresponde
                if base_episodes_data:
                    season1 = next((s for s in seasons if s.get("number") == 1), None)
                    if not season1:
                        season1 = {"number": 1, "episodes": []}
                        seasons.append(season1)
                        existing["seasons"] = seasons
                    existing_eps_1 = {e.get("number") for e in season1["episodes"]}
                    for ep in base_episodes_data:
                        if ep.get("number") not in existing_eps_1:
                            season1["episodes"].append(ep)

                logger.info(f"✅ Anime agregado: {base_title} - Temporada {season_number}")
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error procesando anime {anime.get('title')}: {e}")

    def guardar_animes(self, output_file: str = "anime2.json"):
        """Guarda la lista de animes en JSON."""
        try:
            full_path = os.path.join(self._workspace_root(), output_file)

            # Merge con existentes (ya están en self.animes)
            final = list({s.get("tmdb_id"): s for s in self.animes if s.get("tmdb_id")}.values())
            
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Guardados {len(final)} animes en {full_path}")

        except Exception as e:
            logger.error(f"Error guardando animes: {e}")

    def _guardar_legacy(self):
        """Guarda anime.json si fue modificado (tras borrar entradas movidas)."""
        if not self.legacy_modified:
            return
        try:
            full_path = os.path.join(self._workspace_root(), "anime.json")
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(self.legacy_animes, f, indent=4, ensure_ascii=False)
            logger.info(f"💾 anime.json actualizado ({len(self.legacy_animes)} animes)")
        except Exception as e:
            logger.error(f"Error guardando anime.json: {e}")

    def _cargar_animes_existentes(self, output_file: str = "anime2.json"):
        """Carga animes existentes del JSON destino al inicio."""
        try:
            full_path = os.path.join(self._workspace_root(), output_file)
            
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    self.animes = json.load(f)
                    logger.info(f"📂 Cargados {len(self.animes)} animes de {output_file}")
            else:
                logger.info(f"📂 No existe {output_file}, iniciando desde cero")
        except Exception as e:
            logger.warning(f"No se pudo cargar {output_file}: {e}")

    def _cargar_legacy(self):
        """Carga anime.json (legacy) para verificar duplicados."""
        try:
            full_path = os.path.join(self._workspace_root(), "anime.json")
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    self.legacy_animes = json.load(f)
                    logger.info(f"📂 Cargados {len(self.legacy_animes)} animes de anime.json (legacy)")
            else:
                logger.info("📂 No existe anime.json (legacy)")
        except Exception as e:
            logger.warning(f"No se pudo cargar anime.json: {e}")

    def _buscar_en_legacy(self, tmdb_id: int) -> dict | None:
        """Busca un anime en anime.json por tmdb_id."""
        if not tmdb_id:
            return None
        return next((a for a in self.legacy_animes if a.get("tmdb_id") == tmdb_id), None)

    def _mover_de_legacy(self, tmdb_id: int) -> dict | None:
        """Mueve un anime de anime.json a anime2.json (lo borra de legacy y lo retorna)."""
        legacy = self._buscar_en_legacy(tmdb_id)
        if not legacy:
            return None
        self.legacy_animes = [a for a in self.legacy_animes if a.get("tmdb_id") != tmdb_id]
        self.legacy_modified = True
        logger.info(f"📦 Movido de anime.json → anime2.json: {legacy.get('title')}")
        return legacy

    def _contar_episodios(self, anime_entry: dict, season_number: int) -> set:
        """Retorna set de números de episodio existentes en una temporada."""
        season = next((s for s in anime_entry.get("seasons", []) if s.get("number") == season_number), None)
        if not season:
            return set()
        return {e.get("number") for e in season.get("episodes", [])}

    def procesar_url(self, anime_url: str):
        """Procesa un anime específico por URL."""
        logger.info(f"\n🎯 Procesando URL: {anime_url}")
        
        info = self.extraer_info_anime(anime_url)
        if not info:
            logger.error(f"No se pudo extraer info de {anime_url}")
            return
        
        tmdb_id = info.get("tmdb_id")
        base_title = info.get("title")
        season_number = info.get("season_number", 1)
        base_url = info.get("base_url")
        
        logger.info(f"📺 Anime: {base_title} (Temporada {season_number})")
        logger.info(f"   TMDB ID: {tmdb_id}")
        
        # Extraer episodios disponibles en la web
        episodios = self.extraer_episodios(anime_url)
        logger.info(f"   Episodios en la web: {len(episodios)}")
        
        if not episodios:
            logger.warning("No se encontraron episodios")
            return
        
        eps_web = {ep.get("number") for ep in episodios}
        
        # === VERIFICAR EN LEGACY (anime.json) ===
        legacy_entry = self._buscar_en_legacy(tmdb_id)
        if legacy_entry:
            legacy_eps = self._contar_episodios(legacy_entry, season_number)
            faltan_en_legacy = eps_web - legacy_eps
            
            if not faltan_en_legacy:
                logger.info(f"⏭️ Ya existe completo en anime.json ({len(legacy_eps)} eps). No hacemos nada.")
                return
            else:
                logger.info(f"🔄 Existe en anime.json con {len(legacy_eps)} eps, faltan {len(faltan_en_legacy)}. Moviendo a anime2.json...")
                moved = self._mover_de_legacy(tmdb_id)
                if moved:
                    # Agregar a anime2.json
                    self.animes.append(moved)
        
        # === VERIFICAR EN DESTINO (anime2.json) ===
        existing = next((s for s in self.animes if s.get("tmdb_id") == tmdb_id), None) if tmdb_id else None
        
        if existing:
            existing_eps = self._contar_episodios(existing, season_number)
            nuevos = [ep for ep in episodios if ep.get("number") not in existing_eps]
            logger.info(f"   Ya en anime2.json: {len(existing_eps)} eps, faltan {len(nuevos)}")
        else:
            existing_eps = set()
            nuevos = episodios
        
        if not nuevos:
            logger.info("⏭️ Todos los episodios ya están en anime2.json.")
            return
        
        # Extraer servidores de episodios faltantes
        episodes_data = []
        for i, ep in enumerate(nuevos):
            ep_number = ep.get("number")
            logger.info(f"   Ep {ep_number} ({i+1}/{len(nuevos)})...")
            servers = self.extraer_servidores_episodio(ep["url"])
            title = f"{base_title} Episodio {ep_number}" if ep_number else base_title
            episodes_data.append({
                "title": title,
                "number": ep_number,
                "servers": servers
            })
            time.sleep(0.5)
        
        # También procesar base_url (temporada 1) si es diferente
        base_episodes_data = []
        if base_url and base_url != anime_url and base_url not in self.visited_anime_urls:
            self.visited_anime_urls.add(base_url)
            logger.info(f"   También procesando temporada base: {base_url}")
            base_episodios = self.extraer_episodios(base_url)
            for ep in base_episodios:
                servers = self.extraer_servidores_episodio(ep["url"])
                number = ep.get("number")
                title = f"{base_title} Episodio {number}" if number else base_title
                base_episodes_data.append({
                    "title": title,
                    "number": number,
                    "servers": servers
                })
                time.sleep(0.5)
        
        # Crear o actualizar entrada
        if not existing:
            serie = {
                "tmdb_id": tmdb_id,
                "title": base_title,
                "year": info.get("year", ""),
                "overview": info.get("overview", ""),
                "rating": info.get("rating", 0),
                "genres": info.get("genres", []),
                "seasons": []
            }
            self.animes.append(serie)
            existing = serie
        
        # Agregar temporada
        seasons = existing.get("seasons", [])
        season_obj = next((s for s in seasons if s.get("number") == season_number), None)
        if not season_obj:
            season_obj = {"number": season_number, "episodes": []}
            seasons.append(season_obj)
            existing["seasons"] = seasons
        
        # Agregar episodios sin duplicar
        existing_ep_nums = {e.get("number") for e in season_obj["episodes"]}
        added = 0
        for ep in episodes_data:
            if ep.get("number") not in existing_ep_nums:
                season_obj["episodes"].append(ep)
                added += 1
        
        # Agregar temporada 1 desde base_url si corresponde
        if base_episodes_data:
            season1 = next((s for s in seasons if s.get("number") == 1), None)
            if not season1:
                season1 = {"number": 1, "episodes": []}
                seasons.append(season1)
                existing["seasons"] = seasons
            existing_eps_1 = {e.get("number") for e in season1["episodes"]}
            for ep in base_episodes_data:
                if ep.get("number") not in existing_eps_1:
                    season1["episodes"].append(ep)
        
        logger.info(f"✅ {base_title} - Temporada {season_number}: {added} episodios nuevos en anime2.json")

    def run(self, max_animes: int = None, max_pages: int = None, url: str = None, output_file: str = "anime2.json"):
        logger.info("Iniciando scraper de animes desde ww1.henaojara.net...")
        self._cargar_animes_existentes(output_file)
        self._cargar_legacy()
        
        if url:
            self.procesar_url(url)
        else:
            self.procesar_animes(max_animes=max_animes, max_pages=max_pages)
        
        self.guardar_animes(output_file)
        self._guardar_legacy()
        logger.info(f"✅ Scraping completado. Total en {output_file}: {len(self.animes)} animes")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scraper de animes desde ww1.henaojara.net")
    parser.add_argument("--url", type=str, default=None, help="URL de un anime específico (ej: https://ww1.henaojara.net/anime/naruto-shippuden)")
    parser.add_argument("--output", type=str, default="anime2.json", help="Archivo de salida (default: anime2.json)")
    parser.add_argument("--max-animes", type=int, default=None, help="Número máximo de animes (default: todos)")
    parser.add_argument("--max-pages", type=int, default=None, help="Número máximo de páginas (default: todas)")

    args = parser.parse_args()

    if args.url:
        scraper = HenaojaraAnimeScraper()
        scraper.run(url=args.url, output_file=args.output)
    else:
        max_pages = args.max_pages
        if max_pages is None:
            try:
                raw = input("¿Cuántas páginas quieres extraer? (Enter = todas): ").strip()
                if raw:
                    max_pages = int(raw)
            except Exception:
                max_pages = None

        scraper = HenaojaraAnimeScraper()
        scraper.run(max_animes=args.max_animes, max_pages=max_pages, output_file=args.output)


if __name__ == "__main__":
    main()
