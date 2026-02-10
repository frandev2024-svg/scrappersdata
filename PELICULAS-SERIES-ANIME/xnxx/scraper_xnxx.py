"""
Scraper basico para resultados de busqueda en xnxx.es
Navega por la grilla, entra a cada video y extrae metadatos.
Guarda xnxx.json en el root del workspace.
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.xnxx.es"
START_URL = "https://www.xnxx.es/search/porno+en+espanol?top="
DEFAULT_MAX_PAGES = 3
REQUEST_DELAY_SEC = 1.0

# URLs de búsqueda por categoría
SEARCH_CATEGORIES: Dict[str, str] = {
    "porno_espanol": "https://www.xnxx.es/search/porno+en+espanol?top=",
    "familial_relations": "https://www.xnxx.es/search/familial_relations?id=86963713",
    "milf": "https://www.xnxx.es/search/milf?id=87551937",
    "big_cock": "https://www.xnxx.es/search/big_cock?id=41084707",
    "casero": "https://www.xnxx.es/search/casero?top&id=78663447",
    "skinny": "https://www.xnxx.es/search/skinny?top&id=82232493",
    "mamada": "https://www.xnxx.es/search/mamada?top&id=60590263",
}

# Optional filter to skip risky keywords
EXCLUDE_KEYWORDS: List[str] = []

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class XnxxScraper:
    def __init__(
        self,
        start_url: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        exclude_keywords: Optional[List[str]] = None,
        push_to_repo: bool = False,
        repo_path: Optional[str] = None,
    ):
        self.start_url = start_url
        self.max_pages = max_pages
        self.exclude_keywords = [k.lower() for k in (exclude_keywords or EXCLUDE_KEYWORDS)]
        self.push_to_repo = push_to_repo
        self.repo_path = repo_path or self._default_repo_path()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        self.seen_urls = set()

    def _workspace_root(self) -> str:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(script_dir, "..", ".."))

    def _get_html(self, url: str, referer: Optional[str] = None, timeout: int = 15) -> str:
        headers = {}
        if referer:
            headers["Referer"] = referer
            headers["Origin"] = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"

        actual_url = url
        if url.startswith("view-source:"):
            actual_url = url[len("view-source:"):]

        response = self.session.get(actual_url, timeout=timeout, headers=headers or None)
        response.encoding = "utf-8"
        return response.text

    def _default_repo_path(self) -> str:
        return os.path.join(
            self._workspace_root(),
            "PELICULAS-SERIES-ANIME",
            "peliculas",
            "scrappersdata",
        )

    def _sync_to_repo(self, json_path: str) -> None:
        git_dir = os.path.join(self.repo_path, ".git")
        if not os.path.isdir(git_dir):
            return

        dest_path = os.path.join(self.repo_path, "xnxx.json")
        shutil.copyfile(json_path, dest_path)

        subprocess.run(["git", "-C", self.repo_path, "add", "xnxx.json"], check=False)
        diff_result = subprocess.run(["git", "-C", self.repo_path, "diff", "--cached", "--quiet"], check=False)
        if diff_result.returncode == 0:
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        subprocess.run(
            ["git", "-C", self.repo_path, "commit", "-m", f"Update xnxx.json {timestamp}"],
            check=False,
        )
        subprocess.run(["git", "-C", self.repo_path, "push"], check=False)

    def _is_excluded(self, text: str) -> bool:
        if not self.exclude_keywords:
            return False
        text_low = text.lower()
        return any(k in text_low for k in self.exclude_keywords)

    def _extract_grid_videos(self, page_url: str) -> Tuple[List[Dict], Optional[str]]:
        results: List[Dict] = []
        next_url = None

        try:
            html = self._get_html(page_url, referer=BASE_URL)
            soup = BeautifulSoup(html, "html.parser")

            grid = soup.select_one("#content-thumbs .mozaique")
            if not grid:
                logger.warning("No se encontro grilla en %s", page_url)
                return results, None

            for item in grid.select(".thumb-block"):
                link = item.select_one(".thumb a[href]")
                if not link:
                    continue
                href = link.get("href", "")
                if not href or "/video-" not in href:
                    continue
                if "/search/gold/" in href:
                    continue

                title_elem = item.select_one(".thumb-under a[title]") or item.select_one(".thumb-under a")
                title = title_elem.get("title", "").strip() if title_elem else ""
                if not title and title_elem:
                    title = title_elem.get_text(strip=True)
                if self._is_excluded(title):
                    continue

                video_url = urljoin(BASE_URL, href)
                if video_url in self.seen_urls:
                    continue
                self.seen_urls.add(video_url)

                uploader_elem = item.select_one(".uploader .name")
                uploader = uploader_elem.get_text(strip=True) if uploader_elem else ""

                meta_elem = item.select_one(".metadata")
                meta_text = meta_elem.get_text(" ", strip=True) if meta_elem else ""

                quality_elem = item.select_one(".video-hd")
                quality = self._extract_quality(quality_elem.get_text(" ", strip=True) if quality_elem else "")

                views_elem = item.select_one(".metadata .right")
                views_text, views_number = self._parse_views_text(views_elem.get_text(" ", strip=True) if views_elem else "")
                duration_text, duration_seconds = self._parse_duration_text(meta_text)

                results.append({
                    "url": video_url,
                    "title": title,
                    "uploader": uploader,
                    "meta": meta_text,
                    "quality": quality,
                    "views_text": views_text,
                    "views": views_number,
                    "duration_text": duration_text,
                    "duration_seconds": duration_seconds,
                })

            pagination = soup.select_one(".pagination")
            if pagination:
                next_link = pagination.select_one("a.next")
                if next_link and next_link.get("href"):
                    next_url = urljoin(BASE_URL, next_link["href"])
        except Exception as exc:
            logger.error("Error extrayendo grilla %s: %s", page_url, exc)

        return results, next_url

    def _parse_embed_url(self, html: str, soup: BeautifulSoup) -> str:
        input_elem = soup.select_one("input#copy-video-embed")
        if input_elem and input_elem.get("value"):
            value = input_elem.get("value")
            match = re.search(r'src=\"([^\"]+)\"', value)
            if match:
                return match.group(1)

        match = re.search(r"https?://www\.xnxx\.es/embedframe/[a-z0-9]+", html)
        if match:
            return match.group(0)

        return ""

    def _extract_thumbnail_url(self, soup: BeautifulSoup, html: str) -> str:
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            return og_image.get("content")

        og_match = re.search(r"<meta\s+property=\"og:image\"\s+content=\"([^\"]+)\"", html)
        if og_match:
            return og_match.group(1)

        img_elem = soup.select_one("#html5video .video-pic img")
        if img_elem and img_elem.get("src"):
            return img_elem.get("src")

        match = re.search(r"background-image:\s*url\(&quot;([^\"]+)&quot;\)", html)
        if match:
            return match.group(1)

        return ""

    def _extract_quality(self, text: str) -> str:
        match = re.search(r"(\d{3,4}p)", text.lower())
        return match.group(1) if match else text.strip()

    def _parse_views_text(self, text: str) -> Tuple[str, Optional[int]]:
        if not text:
            return "", None
        match = re.search(r"([0-9]+(?:[\.,][0-9]+)?)\s*([KMB])?", text)
        if not match:
            return text, None
        number_raw = match.group(1)
        suffix = match.group(2)
        try:
            number = float(number_raw.replace(".", "").replace(",", "."))
        except Exception:
            return text, None
        multiplier = 1
        if suffix == "K":
            multiplier = 1_000
        elif suffix == "M":
            multiplier = 1_000_000
        elif suffix == "B":
            multiplier = 1_000_000_000
        return text, int(number * multiplier)

    def _parse_duration_text(self, text: str) -> Tuple[str, Optional[int]]:
        if not text:
            return "", None
        hours = 0
        minutes = 0
        seconds = 0

        match_hours = re.search(r"(\d+)\s*h", text)
        match_minutes = re.search(r"(\d+)\s*min", text)
        match_seconds = re.search(r"(\d+)\s*sec", text)

        if match_hours:
            hours = int(match_hours.group(1))
        if match_minutes:
            minutes = int(match_minutes.group(1))
        if match_seconds:
            seconds = int(match_seconds.group(1))

        total_seconds = hours * 3600 + minutes * 60 + seconds
        if total_seconds == 0:
            return "", None

        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}min")
        if seconds and not parts:
            parts.append(f"{seconds}sec")
        duration_text = " ".join(parts)
        return duration_text, total_seconds

    def _parse_meta_text(self, meta_text: str) -> Tuple[str, Optional[int]]:
        if not meta_text:
            return "", None
        return self._parse_duration_text(meta_text)

    def _extract_video_details(self, video_url: str) -> Optional[Dict]:
        try:
            html = self._get_html(video_url, referer=BASE_URL)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            title_elem = soup.select_one("#video-content-metadata .video-title strong")
            if title_elem:
                title = title_elem.get_text(strip=True)

            uploader_elem = soup.select_one("#video-content-metadata .metadata a")
            uploader = uploader_elem.get_text(strip=True) if uploader_elem else ""

            meta_span = soup.select_one("#video-content-metadata .metadata")
            meta_text = meta_span.get_text(" ", strip=True) if meta_span else ""
            duration_text, duration_seconds = self._parse_meta_text(meta_text)
            quality = self._extract_quality(meta_text)

            description_elem = soup.select_one("#video-content-metadata .video-description")
            description = description_elem.get_text(" ", strip=True) if description_elem else ""

            tags = []
            for tag in soup.select("#video-content-metadata .video-tags a.is-keyword"):
                tag_text = tag.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

            rating_elem = soup.select_one("#video-votes .rating-box.value")
            rating = rating_elem.get_text(strip=True) if rating_elem else ""

            good_votes = ""
            bad_votes = ""
            good_elem = soup.select_one("#video-votes .vote-action-good .value")
            bad_elem = soup.select_one("#video-votes .vote-action-bad .value")
            if good_elem:
                good_votes = good_elem.get_text(strip=True)
            if bad_elem:
                bad_votes = bad_elem.get_text(strip=True)

            download_link = ""
            download_elem = soup.select_one("#tabDownload a[href]")
            if download_elem:
                download_link = download_elem.get("href", "")

            embed_url = self._parse_embed_url(html, soup)
            thumbnail_url = self._extract_thumbnail_url(soup, html)

            return {
                "url": video_url,
                "title": title,
                "uploader": uploader,
                "meta": meta_text,
                "description": description,
                "tags": tags,
                "rating": rating,
                "votes_good": good_votes,
                "votes_bad": bad_votes,
                "download_url": download_link,
                "embed_url": embed_url,
                "thumbnail_url": thumbnail_url,
                "duration_text": duration_text,
                "duration_seconds": duration_seconds,
                "quality": quality,
            }
        except Exception as exc:
            logger.error("Error extrayendo video %s: %s", video_url, exc)
            return None

    def _load_existing(self, output_path: str) -> Dict[str, Dict]:
        if not os.path.exists(output_path):
            return {}
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {item.get("url", ""): item for item in data if isinstance(item, dict)}
            if isinstance(data, dict):
                return data
        except Exception as exc:
            logger.warning("No se pudo leer %s: %s", output_path, exc)
        return {}

    def _write_output(self, items: List[Dict]) -> str:
        output_path = os.path.join(self._workspace_root(), "xnxx.json")
        existing = self._load_existing(output_path)

        for item in items:
            key = item.get("url")
            if not key:
                continue
            existing[key] = item

        output_list = list(existing.values())
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_list, f, ensure_ascii=False, indent=2)

        return output_path

    def _scrape_url(self, start_url: str, category: str = "") -> List[Dict]:
        """Scrape una URL de búsqueda específica y devuelve los resultados."""
        current_url = start_url
        page_count = 0
        results: List[Dict] = []

        while current_url and page_count < self.max_pages:
            page_count += 1
            logger.info("Procesando pagina %s", current_url)
            grid_items, next_url = self._extract_grid_videos(current_url)

            for item in grid_items:
                video_url = item.get("url", "")
                if not video_url:
                    continue
                details = self._extract_video_details(video_url)
                if not details:
                    continue

                merged = dict(item)
                for key, value in details.items():
                    if value is None or value == "":
                        continue
                    merged[key] = value
                merged["scraped_at"] = datetime.now(timezone.utc).isoformat()
                if category:
                    merged["category"] = category
                results.append(merged)

                time.sleep(REQUEST_DELAY_SEC)

            current_url = next_url

        return results

    def run(self) -> str:
        results = self._scrape_url(self.start_url)
        output_path = self._write_output(results)
        if self.push_to_repo:
            self._sync_to_repo(output_path)
        logger.info("Guardado: %s", output_path)
        return output_path

    def run_all_categories(self, categories: Optional[List[str]] = None) -> str:
        """Scrape todas las categorías o las especificadas."""
        all_results: List[Dict] = []
        
        cats_to_scrape = categories if categories else list(SEARCH_CATEGORIES.keys())
        
        for cat_name in cats_to_scrape:
            if cat_name not in SEARCH_CATEGORIES:
                logger.warning("Categoría desconocida: %s", cat_name)
                continue
            
            cat_url = SEARCH_CATEGORIES[cat_name]
            logger.info("=== Scrapeando categoría: %s ===", cat_name)
            results = self._scrape_url(cat_url, category=cat_name)
            all_results.extend(results)
            logger.info("Obtenidos %d videos de %s", len(results), cat_name)

        output_path = self._write_output(all_results)
        if self.push_to_repo:
            self._sync_to_repo(output_path)
        logger.info("Total guardado: %s (%d videos nuevos)", output_path, len(all_results))
        return output_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper XNXX")
    parser.add_argument("--start-url", default=START_URL)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SEC)
    parser.add_argument("--push", action="store_true", help="Sube xnxx.json al repo scrappersdata")
    parser.add_argument("--repo-path", default=None, help="Ruta local del repo scrappersdata")
    parser.add_argument("--all-categories", action="store_true", help="Scrapea todas las categorías definidas")
    parser.add_argument("--categories", nargs="+", choices=list(SEARCH_CATEGORIES.keys()),
                        help="Categorías específicas a scrapear")
    parser.add_argument("--list-categories", action="store_true", help="Lista las categorías disponibles")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    
    if args.list_categories:
        print("Categorías disponibles:")
        for name, url in SEARCH_CATEGORIES.items():
            print(f"  {name}: {url}")
        exit(0)
    
    REQUEST_DELAY_SEC = args.delay
    scraper = XnxxScraper(
        start_url=args.start_url,
        max_pages=args.max_pages,
        push_to_repo=args.push,
        repo_path=args.repo_path,
    )
    
    if args.all_categories:
        scraper.run_all_categories()
    elif args.categories:
        scraper.run_all_categories(args.categories)
    else:
        scraper.run()
