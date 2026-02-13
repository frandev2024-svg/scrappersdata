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
CHATGPT_CACHE_FILE = BASE_DIR / "chatgpt_cache.json"

# Configuración de OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()  # Modelo económico
USE_CHATGPT = os.environ.get("USE_CHATGPT", "false").lower() == "true"

# Configuración de GitHub
REPO_PATH = BASE_DIR / "PELICULAS-SERIES-ANIME" / "peliculas" / "scrappersdata"

ELCANALDEPORTIVO_URL = "https://elcanaldeportivo.com/partidos.json"
STREAMX10_URL = "https://streamx10.cloud/json/agenda345.json"
BOLALOCA_URL = "https://bolaloca.my/"
ANTENASPORT_URL = "https://antenasport.top/index2.txt"
PIRLOTV_URL = "https://pirlotvoficial.com/"
TVLIBREE_URL = "https://tvlibree.com/agenda/"
TVTVHD_URL = "https://tvtvhd.com/eventos/"
TVTVHD_JSON_URL = "https://pltvhd.com/diaries.json"

TIMEOUT_SEC = 20

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==================== MAPAS DE LOGOS Y LIGAS ====================

# Logos por liga/competición (URLs de imágenes oficiales o conocidas)
LIGA_LOGOS: Dict[str, str] = {
    # Fútbol - Ligas Nacionales
    "premier league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/23.png",
    "la liga": "https://bestleague.world/jr/34.png",
    "laliga": "https://bestleague.world/jr/34.png",
    "serie a": "https://bestleague.world/jr/37.png",
    "bundesliga": "https://bestleague.world/jr/96.png",
    "ligue 1": "https://bestleague.world/jr/45.png",
    "eredivisie": "https://bestleague.world/jr/38.png",
    "primeira liga": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/14.png",
    "liga portugal": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/14.png",
    "superliga argentina": "https://elcanaldeportivo.com/img/ar.png",
    "liga profesional argentina": "https://bestleague.world/jr/55.png",
    "liga profesional": "https://bestleague.world/jr/55.png",
    "futbol argentino": "https://bestleague.world/jr/55.png",
    "liga 1": "https://bestleague.world/jr/127.png",
    "liga 1 peru": "https://bestleague.world/jr/127.png",
    
    "torneo lfp": "https://elcanaldeportivo.com/img/ar.png",
    "brasileirao": "https://a4.espncdn.com/combiner/i?img=%2Fi%2Fleaguelogos%2Fsoccer%2F500%2F85.png",
    "serie a brasil": "https://a4.espncdn.com/combiner/i?img=%2Fi%2Fleaguelogos%2Fsoccer%2F500%2F85.png",
    "serie a bresil": "https://a4.espncdn.com/combiner/i?img=%2Fi%2Fleaguelogos%2Fsoccer%2F500%2F85.png",
    "campeonato brasileno": "https://a4.espncdn.com/combiner/i?img=%2Fi%2Fleaguelogos%2Fsoccer%2F500%2F85.png",
    "campeonato carioca": "https://bestleague.world/jr/79.png",
    "liga mx": "https://bestleague.world/jr/69.png",
    "liga de expansion mx": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2306.png",
    "expansion mx": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2306.png",
    "mls": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/19.png",
    "championship": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/24.png",
    "scottish premiership": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/45.png",
    
    # Fútbol - Competiciones UEFA
    "champions league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2.png",
    "uefa champions league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2.png",
    "europa league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2310.png",
    "uefa europa league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/2310.png",
    "conference league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/5765.png",
    "uefa conference league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/5765.png",
    "nations league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/10784.png",
    "uefa nations league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/10784.png",
    "eliminatorias uefa": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    "euro": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    "eurocopa": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    
    # Fútbol - Competiciones CONMEBOL
    "copa libertadores": "https://logodownload.org/wp-content/uploads/2018/10/copa-libertadores-logo.png",
    "libertadores": "https://logodownload.org/wp-content/uploads/2018/10/copa-libertadores-logo.png",
    "copa sudamericana": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/8.png",
    "sudamericana": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/8.png",
    "eliminatorias sudamericanas": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/85.png",
    "eliminatorias conmebol": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/85.png",
    "copa america": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/3.png",
    
    # Fútbol - Otras competiciones
    "copa del rey": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/553.png",
    "fa cup": "https://bestleague.world/jr/61.png",
    "womens super league": "https://bestleague.world/jr/61.png",
    "carabao cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/37.png",
    "efl cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/37.png",
    "dfb pokal": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/529.png",
    "coupe de france": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/526.png",
    "coppa italia": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/522.png",
    "taca de portugal": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/555.png",
    "copa argentina": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/1297.png",
    "copa do brasil": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/521.png",
    "club world cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/350.png",
    "mundial de clubes": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/350.png",
    
    # Fútbol - Selecciones
    "world cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    "mundial": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    "fifa world cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    "amistoso internacional": "https://static.futbolenlatv.com/img/32/20130618113222-futbol.png",
    "friendly": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/4.png",
    
    # Fútbol - AFC
    "afc champions league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/350.png",
    "afc champions league elite": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/350.png",
    "afc champions league two": "https://cdn-img.zerozero.pt/img/logos/competicoes/1312_imgbank_cl2_20240819154152.png",
    "j league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/106.png",
    "k league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/105.png",
    "saudi pro league": "https://bestleague.world/jr/104.png",
    
    # Baloncesto
    "nba": "https://bestleague.world/img/nba.svg",
    "euroleague": "https://yt3.googleusercontent.com/SDKEtv224BImqVHSPNVrg22iL4ZGT_eB2spweT6B_0oATgxRsAUNFVgq80wM3yO4hfhMC6uZUQ=s900-c-k-c0x00ffffff-no-rj",
    "euroliga": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/basketball/500/11.png",
    "acb": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/basketball/500/11.png",
    "liga endesa": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/basketball/500/11.png",
    "ncaa basketball": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/ncaa.png",
    # Básquet genérico (fallback para cualquier liga de basket no mapeada)
    "basquet": "https://png.pngtree.com/png-vector/20250708/ourmid/pngtree-orange-basketball-png-image_16721120.webp",
    "basketball": "https://png.pngtree.com/png-vector/20250708/ourmid/pngtree-orange-basketball-png-image_16721120.webp",
    
    # Tenis
    "atp": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/atp.png",
    "wta": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/wta.png",
    "australian open": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/172.png",
    "roland garros": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/171.png",
    "wimbledon": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/173.png",
    "us open": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/174.png",
    "davis cup": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/172.png",
    "copa davis": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/tennis/500/172.png",
    "ieb argentina open": "https://static.futbolenlatv.com/img/32/20130618113307-tenis.png",
    "ieb+ argentina open": "https://static.futbolenlatv.com/img/32/20130618113307-tenis.png",
    
    # Fórmula 1
    "formula 1": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/f1.png",
    "f1": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/f1.png",
    "grand prix": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/f1.png",
    "gp": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/f1.png",
    
    # NFL / Fútbol Americano
    "nfl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "super bowl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "ncaa football": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/ncaa.png",
    
    # MLB / Béisbol
    "mlb": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/mlb.png",
    "world series": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/mlb.png",
    
    # NHL / Hockey
    "nhl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nhl.png",
    "stanley cup": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nhl.png",
    
    # UFC / MMA / Boxeo
    "ufc": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/ufc.png",
    "mma": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/ufc.png",
    "boxeo": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/boxing.png",
    "boxing": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/boxing.png",
    
    # Golf
    "pga tour": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/pga.png",
    "pga": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/pga.png",
    "masters": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/pga.png",
    
    # Rugby
    "six nations": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "rugby world cup": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "rugby": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    
    # Ciclismo
    "tour de france": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/cycling.png",
    "giro de italia": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/cycling.png",
    "vuelta a espana": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/cycling.png",
    "ciclismo": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/cycling.png",
    
    # AFC / Asia
    "afc ligue des champions": "https://upload.wikimedia.org/wikipedia/fr/f/f5/Ligue_des_champions_AFC_-_Logo.png",
    "afc champions": "https://upload.wikimedia.org/wikipedia/fr/f/f5/Ligue_des_champions_AFC_-_Logo.png",
    
    # Baloncesto adicional
    "basketball": "https://raw.githubusercontent.com/frandev2024-svg/scrappersdata/refs/heads/main/basquet.png",
    "aba liga": "https://images.eurohoops.net/2020/05/ddb81d3e-aba-league-625x375.jpg",
    "basketball aba liga": "https://images.eurohoops.net/2020/05/ddb81d3e-aba-league-625x375.jpg",
    
    # CONCACAF
    "concacaf champions cup": "https://www.concacaf.com/media/aqqka5ga/ccc_primary_white.png",
    "concacaf chamnpions cup": "https://www.concacaf.com/media/aqqka5ga/ccc_primary_white.png",
    "copa de campeones de la concacaf": "https://www.concacaf.com/media/aqqka5ga/ccc_primary_white.png",
    "concacaf": "https://www.concacaf.com/media/aqqka5ga/ccc_primary_white.png",
    
    # Olimpiadas / Hockey
    "winter olympics": "https://upload.wikimedia.org/wikipedia/en/thumb/1/18/Ice_hockey_2016_YOG.svg/1280px-Ice_hockey_2016_YOG.svg.png",
    "ice hockey winter olympics": "https://upload.wikimedia.org/wikipedia/en/thumb/1/18/Ice_hockey_2016_YOG.svg/1280px-Ice_hockey_2016_YOG.svg.png",
    "hockey men ice hockey winter olympics": "https://upload.wikimedia.org/wikipedia/en/thumb/1/18/Ice_hockey_2016_YOG.svg/1280px-Ice_hockey_2016_YOG.svg.png",
    "hockey hielo juegos olimpicos": "https://upload.wikimedia.org/wikipedia/en/thumb/1/18/Ice_hockey_2016_YOG.svg/1280px-Ice_hockey_2016_YOG.svg.png",
    "olympics": "https://upload.wikimedia.org/wikipedia/en/thumb/1/18/Ice_hockey_2016_YOG.svg/1280px-Ice_hockey_2016_YOG.svg.png",
    
    # Colombia
    "liga betplay": "https://bestleague.world/jr/118.png",
    "betplay": "https://bestleague.world/jr/118.png",
    
    # Serbia
    "serbia cup": "https://upload.wikimedia.org/wikipedia/en/f/f1/Serbian_Cup.png",
    "serbian cup": "https://upload.wikimedia.org/wikipedia/en/f/f1/Serbian_Cup.png",
    
    # Ligas adicionales con logos genéricos de ESPN o Wikipedia
    "la liga 2": "https://bestleague.world/jr/34.png",
    "laliga 2": "https://bestleague.world/jr/34.png",
    "serie b": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/12.png",
    "swiss super league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/48.png",
    "super lig": "https://bestleague.world/jr/123.png",
    "bundesliga 2": "https://bestleague.world/jr/96.png",
    "super league greece": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/47.png",
    "ekstraklasa": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "hnl": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "serbia superliga": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "league one": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/25.png",
    "league two": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/26.png",
    "liga portugal": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/14.png",
    "scottish premiership": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/45.png",
    "scottish premier league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/45.png",
    "scottish championship": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/45.png",
    
    # ============================================================
    # AUTOMOVILISMO
    # ============================================================
    # Monoplazas
    "formula 2": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "fia formula 2": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "formula 3": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "fia formula 3": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "indycar": "https://cdn.worldvectorlogo.com/logos/indycar-series.svg",
    "indycar series": "https://cdn.worldvectorlogo.com/logos/indycar-series.svg",
    "super formula": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    # Eléctricos
    "formula e": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Formula-e-logo-championship_2023.svg/3840px-Formula-e-logo-championship_2023.svg.png",
    # Rally
    "wrc": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "world rally championship": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "erc": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "european rally championship": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    # Resistencia
    "wec": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "world endurance championship": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "imsa": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "imsa sportscar": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    # Turismos
    "dtm": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "btcc": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "tcr": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "tcr world tour": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "supercars championship": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "supercars": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    # Motociclismo
    "motogp": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "moto2": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "moto3": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "wsbk": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    "world superbike": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png",
    # NASCAR
    "nascar": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "nascar cup series": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "nascar cup": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "nascar xfinity": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/NASCAR_Xfinity_Series_logo.svg/1280px-NASCAR_Xfinity_Series_logo.svg.png",
    "nascar xfinity series": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/NASCAR_Xfinity_Series_logo.svg/1280px-NASCAR_Xfinity_Series_logo.svg.png",
    "nascar truck": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "nascar truck series": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "daytona 500": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",
    "daytona": "https://cdn.worldvectorlogo.com/logos/nascar-logo-2017.svg",

    # ============================================================
    # BÁSQUET (ampliado)
    # ============================================================
    "g league": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "nba g league": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "nbb": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "liga nacional argentina basquet": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "lnb argentina": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "lnbp": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "liga nacional mexico basquet": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "bsn": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "basketball euroleague": "https://yt3.googleusercontent.com/SDKEtv224BImqVHSPNVrg22iL4ZGT_eB2spweT6B_0oATgxRsAUNFVgq80wM3yO4hfhMC6uZUQ=s900-c-k-c0x00ffffff-no-rj",
    "eurocup": "https://brandcenter.euroleague.net/front/brandcenter/assets/images/euroleague.svg",
    "eurocup basketball": "https://brandcenter.euroleague.net/front/brandcenter/assets/images/euroleague.svg",
    "liga acb": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Acb_2019_logo.svg",
    "lega basket": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "lega basket serie a": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "pro a": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "lnb france": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "bbl": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "bbl basketball": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "vtb united league": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "fiba": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "fiba champions league": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "fiba basketball champions league": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "fiba americup": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "basketball world cup": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",
    "fiba world cup": "https://cdn.worldvectorlogo.com/logos/nba-6.svg",

    # ============================================================
    # HOCKEY SOBRE HIELO (ampliado)
    # ============================================================
    "ahl": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "khl": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/KHL_logo_shield_2016.svg/1280px-KHL_logo_shield_2016.svg.png",
    "shl": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Swedish_Hockey_League_logo.svg/960px-Swedish_Hockey_League_logo.svg.png",
    "liiga": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "del": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "del hockey": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "extraliga": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "national league hockey": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "iihf": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",
    "iihf world championship": "https://upload.wikimedia.org/wikipedia/sco/thumb/3/3a/05_NHL_Shield.svg/1280px-05_NHL_Shield.svg.png",

    # ============================================================
    # FÚTBOL AMERICANO (ampliado)
    # ============================================================
    "cfl": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/CFL_Logo.svg/3840px-CFL_Logo.svg.png",
    "canadian football league": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/CFL_Logo.svg/3840px-CFL_Logo.svg.png",
    "xfl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "usfl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "elf": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "european league of football": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png",
    "ncaa": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/NCAA_logo.svg/250px-NCAA_logo.svg.png",

    # ============================================================
    # FÚTBOL (ampliado)
    # ============================================================
    "campeonato uruguayo": "https://bestleague.world/jr/56.png",
    "primera division uruguay": "https://bestleague.world/jr/56.png",
    "liga chilena": "https://bestleague.world/jr/35.png",
    "primera division chile": "https://bestleague.world/jr/35.png",
    "liga colombiana": "https://bestleague.world/jr/118.png",
    "chinese super league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "chinese super": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "first league bulgaria": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "slovenian prvaliga": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "macedonian first league": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/56.png",
    "liga portugal 2": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/14.png",
    "copa alemania": "https://a.espncdn.com/combiner/i?img=/i/leaguelogos/soccer/500/529.png",

    # ============================================================
    # TENIS (ampliado)
    # ============================================================
    "atp tour": "https://upload.wikimedia.org/wikipedia/he/thumb/3/3f/ATP_Tour_logo.svg/500px-ATP_Tour_logo.svg.png",
    "wta tour": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/WTA_logo_2010.svg/960px-WTA_logo_2010.svg.png",
    "challenger tour": "https://upload.wikimedia.org/wikipedia/he/thumb/3/3f/ATP_Tour_logo.svg/500px-ATP_Tour_logo.svg.png",
    "itf tour": "https://upload.wikimedia.org/wikipedia/he/thumb/3/3f/ATP_Tour_logo.svg/500px-ATP_Tour_logo.svg.png",
    "itf": "https://upload.wikimedia.org/wikipedia/he/thumb/3/3f/ATP_Tour_logo.svg/500px-ATP_Tour_logo.svg.png",
    "billie jean king cup": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/WTA_logo_2010.svg/960px-WTA_logo_2010.svg.png",

    # ============================================================
    # VOLEY
    # ============================================================
    "voley": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",
    "volleyball": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",
    "fivb": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",
    "fivb nations league": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Volleyball_Nations_League_Logo.svg/1280px-Volleyball_Nations_League_Logo.svg.png",
    "nations league volleyball": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Volleyball_Nations_League_Logo.svg/1280px-Volleyball_Nations_League_Logo.svg.png",
    "superlega": "https://upload.wikimedia.org/wikipedia/commons/9/9a/Superlega_Italian_Volleyball_League.png",
    "plusliga": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",
    "liga argentina voley": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",
    "cev champions league": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg/3840px-F%C3%A9d%C3%A9ration_Internationale_de_Volleyball_logo.svg.png",

    # ============================================================
    # BOXEO (ampliado)
    # ============================================================
    "wba": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "world boxing association": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "wbc": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "world boxing council": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "ibf": "https://upload.wikimedia.org/wikipedia/commons/2/2f/IBF.svg",
    "international boxing federation": "https://upload.wikimedia.org/wikipedia/commons/2/2f/IBF.svg",
    "wbo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "world boxing organization": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "the ring": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "top rank": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "matchroom": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "matchroom boxing": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "pbc": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",
    "premier boxing champions": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/WBC_logo.svg/3840px-WBC_logo.svg.png",

    # ============================================================
    # MMA (ampliado)
    # ============================================================
    "bellator": "https://upload.wikimedia.org/wikipedia/commons/e/e6/Bellator_MMA_Logo.svg",
    "bellator mma": "https://upload.wikimedia.org/wikipedia/commons/e/e6/Bellator_MMA_Logo.svg",
    "one championship": "https://upload.wikimedia.org/wikipedia/commons/1/1f/ONE_Championship.png",
    "one fc": "https://upload.wikimedia.org/wikipedia/commons/1/1f/ONE_Championship.png",
    "pfl": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/UFC_Logo.svg/1280px-UFC_Logo.svg.png",
    "professional fighters league": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/UFC_Logo.svg/1280px-UFC_Logo.svg.png",
    "rizin": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/UFC_Logo.svg/1280px-UFC_Logo.svg.png",
    "rizin ff": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/UFC_Logo.svg/1280px-UFC_Logo.svg.png",

    # ============================================================
    # RUGBY (ampliado)
    # ============================================================
    "six nations championship": "https://upload.wikimedia.org/wikipedia/it/thumb/d/d6/Six_Nations_logo.svg/250px-Six_Nations_logo.svg.png",
    "rugby championship": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "top 14": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "premiership rugby": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "united rugby championship": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "urc": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "super rugby": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "super rugby pacific": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",
    "world cup rugby": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/rugby.png",

    # ============================================================
    # CRICKET
    # ============================================================
    "cricket": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "icc": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "icc cricket world cup": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "cricket world cup": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "ipl": "https://upload.wikimedia.org/wikipedia/hi/thumb/8/84/Indian_Premier_League_Official_Logo.svg/1280px-Indian_Premier_League_Official_Logo.svg.png",
    "indian premier league": "https://upload.wikimedia.org/wikipedia/hi/thumb/8/84/Indian_Premier_League_Official_Logo.svg/1280px-Indian_Premier_League_Official_Logo.svg.png",
    "big bash league": "https://upload.wikimedia.org/wikipedia/en/c/c0/Big_Bash_League_%28logo%29.png",
    "big bash": "https://upload.wikimedia.org/wikipedia/en/c/c0/Big_Bash_League_%28logo%29.png",
    "psl": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "pakistan super league": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "the ashes": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",
    "ashes": "https://upload.wikimedia.org/wikipedia/commons/7/71/Icc-logo.svg",

    # ============================================================
    # ESPORTS
    # ============================================================
    "esports": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/UFC_Logo.svg/1280px-UFC_Logo.svg.png",
    "league of legends": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "lol worlds": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "lol": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "cs2": "https://img-cdn.hltv.org/eventlogo/awaDsLUuCqka6Q54efjwK9.png?ixlib=java-2.1.0&s=ac3bb776581548ccd0c490651a37968d",
    "cs2 major": "https://img-cdn.hltv.org/eventlogo/awaDsLUuCqka6Q54efjwK9.png?ixlib=java-2.1.0&s=ac3bb776581548ccd0c490651a37968d",
    "csgo": "https://img-cdn.hltv.org/eventlogo/awaDsLUuCqka6Q54efjwK9.png?ixlib=java-2.1.0&s=ac3bb776581548ccd0c490651a37968d",
    "the international": "https://upload.wikimedia.org/wikipedia/en/9/99/The_International_logo.png",
    "dota 2": "https://upload.wikimedia.org/wikipedia/en/9/99/The_International_logo.png",
    "dota": "https://upload.wikimedia.org/wikipedia/en/9/99/The_International_logo.png",
    "valorant": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "valorant champions": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "overwatch": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
    "overwatch league": "https://i.pinimg.com/736x/6d/3b/cb/6d3bcbd544aaf23fd6f7b5362330775a.jpg",
}

# Mapa de deportes por palabra clave en liga o equipos
DEPORTE_KEYWORDS: Dict[str, List[str]] = {
    "futbol": ["premier", "laliga", "liga", "serie a", "bundesliga", "ligue", "champions", "europa league", 
               "libertadores", "sudamericana", "copa", "fc", "united", "city", "real madrid", "barcelona",
               "juventus", "bayern", "psg", "inter", "milan", "chelsea", "arsenal", "liverpool", "tottenham",
               "boca", "river", "racing", "independiente", "san lorenzo", "futbol", "football", "soccer",
               "eliminatorias", "mundial", "world cup", "euro", "nations league", "friendly", "amistoso",
               "fa cup", "carabao", "dfb pokal", "coppa italia", "coupe de france", "eredivisie", "mls",
               "liga mx", "brasileirao", "superliga", "championship", "conference league", "scottish",
               "primeira liga", "betplay", "concacaf", "saudi pro", "j league", "k league", "afc",
               "super lig", "ekstraklasa", "hnl", "prvaliga", "first league", "swiss super league",
               "serbia superliga", "serbia cup", "copa argentina", "trophee des champions",
               "copa del rey", "super league greece", "liga 1 peru", "campeonato brasileno"],
    "baloncesto": ["nba", "basketball", "euroleague", "euroliga", "acb", "liga endesa", "ncaa basket", 
                   "fiba", "baloncesto", "celtics", "lakers", "warriors", "bulls", "heat", "nets", "knicks",
                   "g league", "nbb", "lnb", "lnbp", "bsn", "eurocup", "liga acb", "lega basket",
                   "pro a", "bbl", "vtb united", "aba liga"],
    "tenis": ["atp", "wta", "tennis", "open", "roland garros", "wimbledon", "grand slam", "davis cup",
              "tenis", "federer", "nadal", "djokovic", "alcaraz", "sinner", "challenger", "itf",
              "billie jean king"],
    "formula1": ["f1", "formula 1", "grand prix", "gp", "ferrari", "mercedes", "red bull racing", 
                 "mclaren", "qualifying", "race", "sprint", "formula 2", "formula 3", "indycar",
                 "formula e", "super formula"],
    "automovilismo": ["wrc", "rally", "wec", "endurance", "imsa", "dtm", "btcc", "tcr", "supercars",
                      "motogp", "moto2", "moto3", "wsbk", "superbike", "nascar", "daytona", "xfinity",
                      "truck series"],
    "futbol_americano": ["nfl", "super bowl", "touchdown", "patriots", "cowboys", "chiefs", "49ers",
                         "ncaa football", "college football", "american football", "cfl", "xfl", "usfl",
                         "elf", "european league of football"],
    "beisbol": ["mlb", "baseball", "beisbol", "world series", "yankees", "dodgers", "red sox", "cubs",
                "home run", "pitcher"],
    "hockey": ["nhl", "hockey", "stanley cup", "rangers", "bruins", "penguins", "maple leafs", "ice hockey",
               "ahl", "khl", "shl hockey", "liiga", "del ice", "extraliga", "iihf"],
    "ufc_mma": ["ufc", "mma", "mixed martial arts", "octagon", "fight night", "ppv", "bellator",
                "one championship", "pfl", "rizin"],
    "boxeo": ["boxing", "boxeo", "peso pesado", "heavyweight", "undisputed", "wbc", "wba", "ibf", "wbo",
              "canelo", "tyson", "fury", "joshua", "top rank", "matchroom", "pbc"],
    "golf": ["pga", "golf", "masters", "the open", "us open golf", "ryder cup", "lpga"],
    "rugby": ["rugby", "six nations", "rugby world cup", "all blacks", "springboks", "wallabies",
              "top 14", "premiership rugby", "urc", "super rugby"],
    "voley": ["voley", "volleyball", "fivb", "superlega", "plusliga", "cev"],
    "cricket": ["cricket", "icc", "ipl", "big bash", "psl cricket", "ashes", "t20"],
    "ciclismo": ["tour de france", "giro", "vuelta", "ciclismo", "cycling", "etapa", "stage"],
    "natacion": ["swimming", "natacion", "olympics swimming", "world aquatics"],
    "atletismo": ["athletics", "atletismo", "marathon", "track and field", "100m", "200m", "diamond league"],
    "esports": ["esports", "lol", "league of legends", "dota", "csgo", "cs2", "valorant", "worlds", "major",
                "overwatch", "the international"],
    "juegos_olimpicos": ["olympic", "olympics", "winter olympics", "summer olympics", "juegos olimpicos"],
}

# ==================== MAPA DE EQUIPOS -> LIGA ====================
# Para inferir la liga cuando la fuente no la proporciona

EQUIPOS_LIGA: Dict[str, str] = {
    # Premier League (Inglaterra)
    "arsenal": "Premier League",
    "aston villa": "Premier League",
    "bournemouth": "Premier League",
    "brentford": "Premier League",
    "brighton": "Premier League",
    "brighton & hove albion": "Premier League",
    "chelsea": "Premier League",
    "crystal palace": "Premier League",
    "everton": "Premier League",
    "fulham": "Premier League",
    "ipswich": "Premier League",
    "ipswich town": "Premier League",
    "leicester": "Premier League",
    "leicester city": "Premier League",
    "liverpool": "Premier League",
    "manchester city": "Premier League",
    "manchester united": "Premier League",
    "newcastle": "Premier League",
    "newcastle united": "Premier League",
    "nottingham forest": "Premier League",
    "southampton": "Premier League",
    "tottenham": "Premier League",
    "tottenham hotspur": "Premier League",
    "west ham": "Premier League",
    "west ham united": "Premier League",
    "wolverhampton": "Premier League",
    "wolverhampton wanderers": "Premier League",
    "wolves": "Premier League",
    
    # Championship (Inglaterra)
    "birmingham": "Championship",
    "birmingham city": "Championship",
    "blackburn": "Championship",
    "bristol city": "Championship",
    "burnley": "Championship",
    "cardiff": "Championship",
    "cardiff city": "Championship",
    "coventry": "Championship",
    "coventry city": "Championship",
    "derby": "Championship",
    "derby county": "Championship",
    "hull city": "Championship",
    "leeds": "Championship",
    "leeds united": "Championship",
    "luton": "Championship",
    "luton town": "Championship",
    "middlesbrough": "Championship",
    "millwall": "Championship",
    "norwich": "Championship",
    "norwich city": "Championship",
    "oxford united": "Championship",
    "plymouth": "Championship",
    "portsmouth": "Championship",
    "preston": "Championship",
    "qpr": "Championship",
    "queens park rangers": "Championship",
    "sheffield united": "Championship",
    "sheffield wednesday": "Championship",
    "stoke": "Championship",
    "stoke city": "Championship",
    "sunderland": "Championship",
    "swansea": "Championship",
    "swansea city": "Championship",
    "watford": "Championship",
    "west brom": "Championship",
    "west bromwich albion": "Championship",
    
    # La Liga (España)
    "alaves": "La Liga",
    "deportivo alaves": "La Liga",
    "athletic": "La Liga",
    "athletic club": "La Liga",
    "athletic bilbao": "La Liga",
    "atletico": "La Liga",
    "atletico madrid": "La Liga",
    "barcelona": "La Liga",
    "betis": "La Liga",
    "real betis": "La Liga",
    "celta": "La Liga",
    "celta de vigo": "La Liga",
    "espanyol": "La Liga",
    "getafe": "La Liga",
    "girona": "La Liga",
    "las palmas": "La Liga",
    "leganes": "La Liga",
    "mallorca": "La Liga",
    "osasuna": "La Liga",
    "rayo": "La Liga",
    "rayo vallecano": "La Liga",
    "real madrid": "La Liga",
    "real sociedad": "La Liga",
    "sevilla": "La Liga",
    "valencia": "La Liga",
    "valladolid": "La Liga",
    "real valladolid": "La Liga",
    "villarreal": "La Liga",
    
    # La Liga 2 (España)
    "almeria": "La Liga 2",
    "burgos": "La Liga 2",
    "cadiz": "La Liga 2",
    "cartagena": "La Liga 2",
    "castellon": "La Liga 2",
    "cordoba": "La Liga 2",
    "eibar": "La Liga 2",
    "elche": "La Liga 2",
    "ferrol": "La Liga 2",
    "granada": "La Liga 2",
    "huesca": "La Liga 2",
    "levante": "La Liga 2",
    "malaga": "La Liga 2",
    "mirandes": "La Liga 2",
    "oviedo": "La Liga 2",
    "real oviedo": "La Liga 2",
    "racing": "La Liga 2",
    "sporting gijon": "La Liga 2",
    "tenerife": "La Liga 2",
    "zaragoza": "La Liga 2",
    "real zaragoza": "La Liga 2",
    
    # Serie A (Italia)
    "atalanta": "Serie A",
    "bologna": "Serie A",
    "cagliari": "Serie A",
    "como": "Serie A",
    "empoli": "Serie A",
    "fiorentina": "Serie A",
    "genoa": "Serie A",
    "inter": "Serie A",
    "internazionale": "Serie A",
    "juventus": "Serie A",
    "lazio": "Serie A",
    "lecce": "Serie A",
    "milan": "Serie A",
    "ac milan": "Serie A",
    "monza": "Serie A",
    "napoli": "Serie A",
    "parma": "Serie A",
    "roma": "Serie A",
    "as roma": "Serie A",
    "torino": "Serie A",
    "udinese": "Serie A",
    "venezia": "Serie A",
    "verona": "Serie A",
    "hellas verona": "Serie A",
    
    # Serie B (Italia)
    "bari": "Serie B",
    "brescia": "Serie B",
    "catanzaro": "Serie B",
    "cesena": "Serie B",
    "cittadella": "Serie B",
    "cosenza": "Serie B",
    "cremonese": "Serie B",
    "frosinone": "Serie B",
    "juve stabia": "Serie B",
    "modena": "Serie B",
    "palermo": "Serie B",
    "pisa": "Serie B",
    "reggiana": "Serie B",
    "salernitana": "Serie B",
    "sampdoria": "Serie B",
    "sassuolo": "Serie B",
    "spezia": "Serie B",
    "sudtirol": "Serie B",
    
    # Bundesliga (Alemania)
    "augsburg": "Bundesliga",
    "bayer leverkusen": "Bundesliga",
    "leverkusen": "Bundesliga",
    "bayern": "Bundesliga",
    "bayern munich": "Bundesliga",
    "bayern munchen": "Bundesliga",
    "bochum": "Bundesliga",
    "borussia dortmund": "Bundesliga",
    "dortmund": "Bundesliga",
    "borussia monchengladbach": "Bundesliga",
    "monchengladbach": "Bundesliga",
    "eintracht frankfurt": "Bundesliga",
    "frankfurt": "Bundesliga",
    "freiburg": "Bundesliga",
    "heidenheim": "Bundesliga",
    "hoffenheim": "Bundesliga",
    "holstein kiel": "Bundesliga",
    "kiel": "Bundesliga",
    "mainz": "Bundesliga",
    "mainz 05": "Bundesliga",
    "rb leipzig": "Bundesliga",
    "leipzig": "Bundesliga",
    "st. pauli": "Bundesliga",
    "stuttgart": "Bundesliga",
    "union berlin": "Bundesliga",
    "werder bremen": "Bundesliga",
    "wolfsburg": "Bundesliga",
    "koln": "Bundesliga",
    "cologne": "Bundesliga",
    
    # Ligue 1 (Francia)
    "angers": "Ligue 1",
    "auxerre": "Ligue 1",
    "brest": "Ligue 1",
    "le havre": "Ligue 1",
    "lens": "Ligue 1",
    "lille": "Ligue 1",
    "lyon": "Ligue 1",
    "olympique lyonnais": "Ligue 1",
    "marseille": "Ligue 1",
    "olympique marseille": "Ligue 1",
    "monaco": "Ligue 1",
    "montpellier": "Ligue 1",
    "nantes": "Ligue 1",
    "nice": "Ligue 1",
    "psg": "Ligue 1",
    "paris saint-germain": "Ligue 1",
    "paris": "Ligue 1",
    "reims": "Ligue 1",
    "rennes": "Ligue 1",
    "saint-etienne": "Ligue 1",
    "strasbourg": "Ligue 1",
    "toulouse": "Ligue 1",
    
    # Eredivisie (Países Bajos)
    "ajax": "Eredivisie",
    "az": "Eredivisie",
    "az alkmaar": "Eredivisie",
    "feyenoord": "Eredivisie",
    "groningen": "Eredivisie",
    "heerenveen": "Eredivisie",
    "heracles": "Eredivisie",
    "nac breda": "Eredivisie",
    "nec": "Eredivisie",
    "psv": "Eredivisie",
    "psv eindhoven": "Eredivisie",
    "sparta rotterdam": "Eredivisie",
    "twente": "Eredivisie",
    "utrecht": "Eredivisie",
    "fc utrecht": "Eredivisie",
    "vitesse": "Eredivisie",
    "volendam": "Eredivisie",
    "waalwijk": "Eredivisie",
    "willem ii": "Eredivisie",
    "fortuna sittard": "Eredivisie",
    "excelsior": "Eredivisie",
    
    # Liga Portugal
    "arouca": "Liga Portugal",
    "avs": "Liga Portugal",
    "benfica": "Liga Portugal",
    "boavista": "Liga Portugal",
    "braga": "Liga Portugal",
    "sporting braga": "Liga Portugal",
    "casa pia": "Liga Portugal",
    "estoril": "Liga Portugal",
    "estrela": "Liga Portugal",
    "famalicao": "Liga Portugal",
    "farense": "Liga Portugal",
    "gil vicente": "Liga Portugal",
    "moreirense": "Liga Portugal",
    "nacional": "Liga Portugal",
    "porto": "Liga Portugal",
    "fc porto": "Liga Portugal",
    "rio ave": "Liga Portugal",
    "santa clara": "Liga Portugal",
    "sporting cp": "Liga Portugal",
    "sporting": "Liga Portugal",
    "vitoria guimaraes": "Liga Portugal",
    "guimaraes": "Liga Portugal",
    
    # Scottish Premiership
    "aberdeen": "Scottish Premiership",
    "celtic": "Scottish Premiership",
    "dundee": "Scottish Premiership",
    "dundee united": "Scottish Premiership",
    "hearts": "Scottish Premiership",
    "hibernian": "Scottish Premiership",
    "kilmarnock": "Scottish Premiership",
    "livingston": "Scottish Premiership",
    "motherwell": "Scottish Premiership",
    "rangers": "Scottish Premiership",
    "ross county": "Scottish Premiership",
    "st. johnstone": "Scottish Premiership",
    "st. mirren": "Scottish Premiership",
    "falkirk": "Scottish Championship",
    
    # Super Lig (Turquía)
    "besiktas": "Super Lig",
    "fenerbahce": "Super Lig",
    "galatasaray": "Super Lig",
    "trabzonspor": "Super Lig",
    
    # Super League (Grecia)
    "aek athens": "Super League Greece",
    "aris": "Super League Greece",
    "asteras tripolis": "Super League Greece",
    "atromitos": "Super League Greece",
    "levadiakos": "Super League Greece",
    "ofi": "Super League Greece",
    "olympiakos": "Super League Greece",
    "olympiakos piraeus": "Super League Greece",
    "panathinaikos": "Super League Greece",
    "panaitolikos": "Super League Greece",
    "paok": "Super League Greece",
    "volos": "Super League Greece",
    "volos nfc": "Super League Greece",
    
    # Swiss Super League
    "basel": "Swiss Super League",
    "grasshoppers": "Swiss Super League",
    "lausanne": "Swiss Super League",
    "lausanne sport": "Swiss Super League",
    "lugano": "Swiss Super League",
    "luzern": "Swiss Super League",
    "servette": "Swiss Super League",
    "sion": "Swiss Super League",
    "st. gallen": "Swiss Super League",
    "thun": "Swiss Super League",
    "winterthur": "Swiss Super League",
    "young boys": "Swiss Super League",
    "zurich": "Swiss Super League",
    
    # Ekstraklasa (Polonia)
    "cracovia": "Ekstraklasa",
    "gornik zabrze": "Ekstraklasa",
    "jagiellonia": "Ekstraklasa",
    "jagiellonia bialystok": "Ekstraklasa",
    "lech poznan": "Ekstraklasa",
    "legia warszawa": "Ekstraklasa",
    "legia": "Ekstraklasa",
    "piast gliwice": "Ekstraklasa",
    "pogon szczecin": "Ekstraklasa",
    "radomiak radom": "Ekstraklasa",
    "rakow czestochowa": "Ekstraklasa",
    "slask wroclaw": "Ekstraklasa",
    "wisla krakow": "Ekstraklasa",
    "widzew lodz": "Ekstraklasa",
    "korona kielce": "Ekstraklasa",
    "motor lublin": "Ekstraklasa",
    "arka gdynia": "Ekstraklasa",
    "katowice": "Ekstraklasa",
    "lechia gdansk": "Ekstraklasa",
    
    # HNL (Croacia)
    "dinamo zagreb": "HNL",
    "hajduk split": "HNL",
    "istra 1961": "HNL",
    "lokomotiva zagreb": "HNL",
    "osijek": "HNL",
    "rijeka": "HNL",
    "slaven koprivnica": "HNL",
    "varazdin": "HNL",
    
    # Serbia SuperLiga
    "crvena zvezda": "Serbia SuperLiga",
    "cukaricki": "Serbia SuperLiga",
    "novi pazar": "Serbia SuperLiga",
    "ofk beograd": "Serbia SuperLiga",
    "partizan": "Serbia SuperLiga",
    "spartak": "Serbia SuperLiga",
    "tsc": "Serbia SuperLiga",
    "vojvodina": "Serbia SuperLiga",
    "zeleznicar": "Serbia SuperLiga",
    "mladost": "Serbia SuperLiga",
    
    # First League (Bulgaria)
    "arda": "First League Bulgaria",
    "botev plovdiv": "First League Bulgaria",
    "cska 1948": "First League Bulgaria",
    "cska sofia": "First League Bulgaria",
    "levski sofia": "First League Bulgaria",
    "lokomotiv plovdiv": "First League Bulgaria",
    "ludogorets": "First League Bulgaria",
    "slavia sofia": "First League Bulgaria",
    "septemvri sofia": "First League Bulgaria",
    "montana": "First League Bulgaria",
    
    # UEFA Champions League (equipos frecuentes)
    "club brugge": "UEFA Champions League",
    "young boys": "UEFA Champions League",
    "salzburg": "UEFA Champions League",
    "shakhtar donetsk": "UEFA Champions League",
    "benfica": "UEFA Champions League",
    "sporting": "UEFA Champions League",
    "crvena zvezda": "UEFA Champions League",
    "ferencvaros": "UEFA Champions League",
    
    # UEFA Europa League (equipos frecuentes)
    "brann": "UEFA Europa League",
    "bodo/glimt": "UEFA Europa League",
    "bodo / glimt": "UEFA Europa League",
    "qarabag": "UEFA Europa League",
    "viktoria plzen": "UEFA Europa League",
    
    # Sudamérica
    "alianza lima": "Liga 1 Peru",
    "2 de mayo": "Liga Paraguaya",
    
    # Otros
    "wrexham": "League One",
    "charlton athletic": "League One",
    "mansfield town": "League Two",
    "salford city": "League Two",
    "port vale": "League Two",
    "burton albion": "League One",
    "grimsby town": "League Two",
    "wigan athletic": "League One",
    
    # NBA - Todos los equipos
    "atlanta hawks": "NBA",
    "boston celtics": "NBA",
    "brooklyn nets": "NBA",
    "charlotte hornets": "NBA",
    "chicago bulls": "NBA",
    "cleveland cavaliers": "NBA",
    "dallas mavericks": "NBA",
    "denver nuggets": "NBA",
    "detroit pistons": "NBA",
    "golden state warriors": "NBA",
    "houston rockets": "NBA",
    "indiana pacers": "NBA",
    "los angeles clippers": "NBA",
    "los angeles lakers": "NBA",
    "memphis grizzlies": "NBA",
    "miami heat": "NBA",
    "milwaukee bucks": "NBA",
    "minnesota timberwolves": "NBA",
    "new orleans pelicans": "NBA",
    "new york knicks": "NBA",
    "oklahoma city thunder": "NBA",
    "orlando magic": "NBA",
    "philadelphia 76ers": "NBA",
    "phoenix suns": "NBA",
    "portland trail blazers": "NBA",
    "sacramento kings": "NBA",
    "san antonio spurs": "NBA",
    "toronto raptors": "NBA",
    "utah jazz": "NBA",
    "washington wizards": "NBA",
    
    # AFC Champions League
    "al nassr": "AFC Champions League",
    "al nassr riyadh": "AFC Champions League",
    "al ahli": "AFC Champions League",
    "al ahli doha": "AFC Champions League",
    "sepahan": "AFC Champions League",
    "arkadag": "AFC Champions League",
    
    # Otras ligas menores
    "kobenhavn": "Danish Superliga",
    "nordsjalland": "Danish Superliga",
    "copenhagen": "Danish Superliga",
    "tondela": "Liga Portugal 2",
    "alverca": "Liga Portugal 2",
    "celje": "Slovenian PrvaLiga",
    "drita": "Kosovar Superliga",
    "skendija 79": "Macedonian First League",
    "samsunspor": "Super Lig",
}

# Banderas por país (fallback cuando no hay logo de liga)
# Usa flagcdn.com para imágenes PNG de banderas
BANDERAS_PAIS: Dict[str, str] = {
    "argentina": "https://flagcdn.com/w320/ar.png",
    "brasil": "https://flagcdn.com/w320/br.png",
    "méxico": "https://flagcdn.com/w320/mx.png",
    "colombia": "https://flagcdn.com/w320/co.png",
    "chile": "https://flagcdn.com/w320/cl.png",
    "perú": "https://flagcdn.com/w320/pe.png",
    "paraguay": "https://flagcdn.com/w320/py.png",
    "uruguay": "https://flagcdn.com/w320/uy.png",
    "ecuador": "https://flagcdn.com/w320/ec.png",
    "venezuela": "https://flagcdn.com/w320/ve.png",
    "bolivia": "https://flagcdn.com/w320/bo.png",
    "estados unidos": "https://flagcdn.com/w320/us.png",
    "canadá": "https://flagcdn.com/w320/ca.png",
    "estados unidos/canadá": "https://flagcdn.com/w320/us.png",
    "inglaterra": "https://flagcdn.com/w320/gb-eng.png",
    "españa": "https://flagcdn.com/w320/es.png",
    "italia": "https://flagcdn.com/w320/it.png",
    "alemania": "https://flagcdn.com/w320/de.png",
    "francia": "https://flagcdn.com/w320/fr.png",
    "portugal": "https://flagcdn.com/w320/pt.png",
    "países bajos": "https://flagcdn.com/w320/nl.png",
    "bélgica": "https://flagcdn.com/w320/be.png",
    "escocia": "https://flagcdn.com/w320/gb-sct.png",
    "gales": "https://flagcdn.com/w320/gb-wls.png",
    "irlanda": "https://flagcdn.com/w320/ie.png",
    "suiza": "https://flagcdn.com/w320/ch.png",
    "austria": "https://flagcdn.com/w320/at.png",
    "turquía": "https://flagcdn.com/w320/tr.png",
    "grecia": "https://flagcdn.com/w320/gr.png",
    "polonia": "https://flagcdn.com/w320/pl.png",
    "croacia": "https://flagcdn.com/w320/hr.png",
    "serbia": "https://flagcdn.com/w320/rs.png",
    "bulgaria": "https://flagcdn.com/w320/bg.png",
    "rumania": "https://flagcdn.com/w320/ro.png",
    "hungría": "https://flagcdn.com/w320/hu.png",
    "república checa": "https://flagcdn.com/w320/cz.png",
    "eslovaquia": "https://flagcdn.com/w320/sk.png",
    "eslovenia": "https://flagcdn.com/w320/si.png",
    "macedonia": "https://flagcdn.com/w320/mk.png",
    "albania": "https://flagcdn.com/w320/al.png",
    "dinamarca": "https://flagcdn.com/w320/dk.png",
    "suecia": "https://flagcdn.com/w320/se.png",
    "noruega": "https://flagcdn.com/w320/no.png",
    "finlandia": "https://flagcdn.com/w320/fi.png",
    "islandia": "https://flagcdn.com/w320/is.png",
    "rusia": "https://flagcdn.com/w320/ru.png",
    "ucrania": "https://flagcdn.com/w320/ua.png",
    "japón": "https://flagcdn.com/w320/jp.png",
    "corea del sur": "https://flagcdn.com/w320/kr.png",
    "china": "https://flagcdn.com/w320/cn.png",
    "india": "https://flagcdn.com/w320/in.png",
    "australia": "https://flagcdn.com/w320/au.png",
    "nueva zelanda": "https://flagcdn.com/w320/nz.png",
    "arabia saudita": "https://flagcdn.com/w320/sa.png",
    "emiratos árabes": "https://flagcdn.com/w320/ae.png",
    "qatar": "https://flagcdn.com/w320/qa.png",
    "sudáfrica": "https://flagcdn.com/w320/za.png",
    "egipto": "https://flagcdn.com/w320/eg.png",
    "marruecos": "https://flagcdn.com/w320/ma.png",
    "costa rica": "https://flagcdn.com/w320/cr.png",
    "panamá": "https://flagcdn.com/w320/pa.png",
    "honduras": "https://flagcdn.com/w320/hn.png",
    "el salvador": "https://flagcdn.com/w320/sv.png",
    "guatemala": "https://flagcdn.com/w320/gt.png",
    "jamaica": "https://flagcdn.com/w320/jm.png",
    "israel": "https://flagcdn.com/w320/il.png",
    "pakistán": "https://flagcdn.com/w320/pk.png",
    # Regiones multi-país
    "europa": "https://flagcdn.com/w320/eu.png",
    "sudamérica": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Flag_of_CONMEBOL.svg/320px-Flag_of_CONMEBOL.svg.png",
    "concacaf": "https://upload.wikimedia.org/wikipedia/en/thumb/7/72/CONCACAF_logo.svg/320px-CONCACAF_logo.svg.png",
    "asia": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d4/Asian_Football_Confederation_%28logo%29.svg/320px-Asian_Football_Confederation_%28logo%29.svg.png",
    "balcanes": "https://flagcdn.com/w320/eu.png",
    "internacional": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Flag_of_the_United_Nations.svg/320px-Flag_of_the_United_Nations.svg.png",
}

# Mapa de país por liga
PAIS_POR_LIGA: Dict[str, str] = {
    "premier league": "Inglaterra",
    "championship": "Inglaterra",
    "fa cup": "Inglaterra",
    "carabao cup": "Inglaterra",
    "efl cup": "Inglaterra",
    "la liga": "España",
    "laliga": "España",
    "laliga hypermotion": "España",
    "copa del rey": "España",
    "serie a": "Italia",
    "coppa italia": "Italia",
    "bundesliga": "Alemania",
    "dfb pokal": "Alemania",
    "ligue 1": "Francia",
    "coupe de france": "Francia",
    "eredivisie": "Países Bajos",
    "primeira liga": "Portugal",
    "liga portugal": "Portugal",
    "taca de portugal": "Portugal",
    "superliga argentina": "Argentina",
    "liga profesional argentina": "Argentina",
    "futbol argentino": "Argentina",
    "copa argentina": "Argentina",
    "brasileirao": "Brasil",
    "serie a brasil": "Brasil",
    "copa do brasil": "Brasil",
    "liga mx": "México",
    "mls": "Estados Unidos",
    "scottish premiership": "Escocia",
    "j league": "Japón",
    "k league": "Corea del Sur",
    "saudi pro league": "Arabia Saudita",
    "champions league": "Europa",
    "europa league": "Europa",
    "conference league": "Europa",
    "nations league": "Europa",
    "copa libertadores": "Sudamérica",
    "copa sudamericana": "Sudamérica",
    "copa america": "Sudamérica",
    "nba": "Estados Unidos",
    "nfl": "Estados Unidos",
    "mlb": "Estados Unidos",
    "nhl": "Estados Unidos/Canadá",
    "ufc": "Internacional",
    "formula 1": "Internacional",
    "f1": "Internacional",
    "liga betplay": "Colombia",
    "betplay": "Colombia",
    "serbia cup": "Serbia",
    "serbian cup": "Serbia",
    "aba liga": "Balcanes",
    "concacaf": "CONCACAF",
    "concacaf champions cup": "CONCACAF",
    "afc champions": "Asia",
    "afc champions league two": "Asia",
    "afc ligue des champions": "Asia",
    "winter olympics": "Internacional",
    "olympics": "Internacional",
    "hockey hielo juegos olimpicos": "Internacional",
    # Ligas adicionales
    "la liga 2": "España",
    "serie b": "Italia",
    "ligue 2": "Francia",
    "2. bundesliga": "Alemania",
    "swiss super league": "Suiza",
    "super lig": "Turquía",
    "super league greece": "Grecia",
    "ekstraklasa": "Polonia",
    "hnl": "Croacia",
    "serbia superliga": "Serbia",
    "first league bulgaria": "Bulgaria",
    "league one": "Inglaterra",
    "league two": "Inglaterra",
    "liga 1 peru": "Perú",
    "liga paraguaya": "Paraguay",
    "uefa europa league": "Europa",
}

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


# ==================== FUNCIONES DE CHATGPT ====================

# Caché en memoria para evitar llamadas repetidas
_chatgpt_cache: Dict[str, Dict[str, str]] = {}


def load_chatgpt_cache() -> Dict[str, Dict[str, str]]:
    """Carga el caché de ChatGPT desde archivo."""
    global _chatgpt_cache
    if CHATGPT_CACHE_FILE.exists():
        try:
            with CHATGPT_CACHE_FILE.open("r", encoding="utf-8") as f:
                _chatgpt_cache = json.load(f)
                logger.info("Caché de ChatGPT cargado: %d entradas", len(_chatgpt_cache))
        except Exception as e:
            logger.warning("Error cargando caché de ChatGPT: %s", e)
            _chatgpt_cache = {}
    return _chatgpt_cache


def save_chatgpt_cache() -> None:
    """Guarda el caché de ChatGPT a archivo."""
    try:
        with CHATGPT_CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(_chatgpt_cache, f, ensure_ascii=False, indent=2)
        logger.info("Caché de ChatGPT guardado: %d entradas", len(_chatgpt_cache))
    except Exception as e:
        logger.warning("Error guardando caché de ChatGPT: %s", e)


def query_chatgpt_for_match_info(equipos: str) -> Dict[str, str]:
    """
    Consulta a ChatGPT para obtener información sobre un partido.
    Retorna dict con: liga, deporte, pais
    """
    global _chatgpt_cache
    
def query_chatgpt_for_match_info(equipos: str, liga_hint: str = "") -> Dict[str, str]:
    """
    Consulta a ChatGPT para inferir liga, deporte y país.
    Se usa solo cuando la inferencia local no alcanza (liga vacía o sin país conocido).
    """
    global _chatgpt_cache

    equipos = equipos or ""
    liga_hint = liga_hint or ""
    if not equipos and not liga_hint:
        return {}

    cache_key = normalize_text(f"{liga_hint}|{equipos}")

    if cache_key in _chatgpt_cache:
        logger.debug("ChatGPT caché hit: %s", equipos)
        return _chatgpt_cache[cache_key]

    if not OPENAI_API_KEY or not USE_CHATGPT:
        return {}

    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        prompt_lines = [
            "Responde SOLO con un JSON válido (sin texto extra) con las claves: liga, deporte, pais.",
            "Si no conoces un dato usa \"\".",
            f"Partido: \"{equipos}\"",
        ]
        if liga_hint:
            prompt_lines.append(f"Liga sugerida: \"{liga_hint}\"")

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "Eres un experto en deportes. Responde solo con JSON."},
                {"role": "user", "content": "\n".join(prompt_lines)},
            ],
            "temperature": 0.1,
            "max_tokens": 120,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code != 200:
            logger.warning("ChatGPT API error %d: %s", response.status_code, response.text[:200])
            return {}

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```json?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        result = json.loads(content)
        result = {
            "liga": result.get("liga", "") or "",
            "deporte": result.get("deporte", "") or "",
            "pais": result.get("pais", "") or "",
        }

        _chatgpt_cache[cache_key] = result
        logger.info("ChatGPT: %s -> %s / %s", equipos, result.get("liga", ""), result.get("pais", ""))

        return result

    except json.JSONDecodeError as e:
        logger.warning("ChatGPT JSON error para '%s': %s", equipos, e)
        return {}
    except Exception as e:
        logger.warning("ChatGPT error para '%s': %s", equipos, e)
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


def infer_deporte(liga: str, equipos: str) -> str:
    """Infiere el deporte basado en liga y equipos."""
    liga_lower = normalize_text(liga)
    
    deporte_map = {
        "futbol": "Fútbol",
        "baloncesto": "Basketball",
        "tenis": "Tenis",
        "formula1": "Fórmula 1",
        "futbol_americano": "Fútbol Americano",
        "beisbol": "Béisbol",
        "hockey": "Hockey",
        "ufc_mma": "MMA",
        "boxeo": "Boxeo",
        "golf": "Golf",
        "rugby": "Rugby",
        "ciclismo": "Ciclismo",
        "natacion": "Natación",
        "atletismo": "Atletismo",
        "automovilismo": "Automovilismo",
        "voley": "Voley",
        "cricket": "Cricket",
        "esports": "Esports",
        "juegos_olimpicos": "Juegos Olímpicos",
    }
    
    # PASO 1: Detección directa por prefijo/nombre de la liga (máxima prioridad)
    if liga_lower.startswith("basketball") or liga_lower in ["nba"]:
        return "Basketball"
    if "olympic" in liga_lower or "olympics" in liga_lower or "juegos olimpicos" in liga_lower:
        return "Juegos Olímpicos"
    if liga_lower.startswith("hockey") or "ice hockey" in liga_lower:
        return "Hockey"
    if "formula 1" in liga_lower or "formula1" in liga_lower or liga_lower == "f1":
        return "Fórmula 1"
    if liga_lower.startswith("rugby"):
        return "Rugby"
    if liga_lower.startswith("tennis") or liga_lower.startswith("tenis"):
        return "Tenis"
    
    # PASO 2: Buscar keywords SOLO en la liga (no en equipos) para evitar falsos positivos
    # (ej: "Girona" no debe matchear "giro" de ciclismo, "Celtic" no debe matchear basket)
    orden_prioridad = [
        "baloncesto", "hockey", "formula1", "automovilismo", "tenis",
        "futbol_americano", "beisbol", "ufc_mma", "boxeo", "golf",
        "rugby", "voley", "cricket", "ciclismo", "natacion", "atletismo",
        "esports", "juegos_olimpicos",
        "futbol",
    ]
    
    for deporte in orden_prioridad:
        keywords = DEPORTE_KEYWORDS.get(deporte, [])
        for keyword in keywords:
            if keyword.lower() in liga_lower:
                return deporte_map.get(deporte, deporte.capitalize())
    
    # PASO 3: Solo si la liga no dio resultado, buscar en equipos (con cuidado)
    # Solo para deportes muy específicos que no se confundan con fútbol
    text_equipos = normalize_text(equipos)
    deportes_seguros_equipos = ["baloncesto", "futbol_americano", "ufc_mma", "boxeo"]
    for deporte in deportes_seguros_equipos:
        keywords = DEPORTE_KEYWORDS.get(deporte, [])
        for keyword in keywords:
            if keyword.lower() in text_equipos:
                return deporte_map.get(deporte, deporte.capitalize())
    
    return "Deportes"


def infer_logo(liga: str, equipos: str) -> str:
    """Infiere el logo basado en la liga o equipos. Si no hay logo, usa bandera del país."""
    text = normalize_text(liga)
    
    # Buscar coincidencia en liga (más largo primero para matchear "afc champions league two" antes que "afc champions")
    best_match = ""
    best_key_len = 0
    for liga_key, logo_url in LIGA_LOGOS.items():
        if liga_key in text and len(liga_key) > best_key_len:
            best_match = logo_url
            best_key_len = len(liga_key)
    if best_match:
        return best_match
    
    # Buscar en equipos también
    text_equipos = normalize_text(equipos)
    for liga_key, logo_url in LIGA_LOGOS.items():
        if liga_key in text_equipos:
            return logo_url
    
    # Fallback por deporte: si es baloncesto, usar logo genérico de basket
    deporte = infer_deporte(liga, equipos)
    if deporte == "Basketball":
        return "https://png.pngtree.com/png-vector/20250708/ourmid/pngtree-orange-basketball-png-image_16721120.webp"
    
    # Fallback: usar bandera del país de la liga
    pais = infer_pais(liga)
    if pais:
        pais_lower = pais.lower()
        if pais_lower in BANDERAS_PAIS:
            return BANDERAS_PAIS[pais_lower]
    
    return ""


def infer_liga_from_equipos(equipos: str) -> str:
    """Infiere la liga basada en los nombres de equipos."""
    if not equipos:
        return ""
    
    text = normalize_text(equipos)
    
    # Buscar cada equipo en el mapa
    for equipo, liga in EQUIPOS_LIGA.items():
        if equipo in text:
            return liga
    
    # Buscar palabras individuales también
    words = text.split()
    for word in words:
        if len(word) >= 4:  # Evitar matches muy cortos
            for equipo, liga in EQUIPOS_LIGA.items():
                if word == equipo or equipo in word:
                    return liga
    
    return ""


def infer_pais(liga: str) -> str:
    """Infiere el país basado en la liga."""
    text = normalize_text(liga)
    
    for liga_key, pais in PAIS_POR_LIGA.items():
        if liga_key in text:
            return pais
    
    return ""


def normalize_liga_name(liga: str) -> str:
    """Normaliza y mejora el nombre de la liga."""
    if not liga:
        return ""
    
    # Mapa de normalizaciones comunes
    normalizaciones = {
        "eng": "Premier League",
        "esp": "La Liga",
        "ger": "Bundesliga",
        "ita": "Serie A",
        "fra": "Ligue 1",
        "arg": "Futbol Argentino",
        "liga profesional argentina": "Futbol Argentino",
        "liga profesional": "Futbol Argentino",
        "torneo lfp": "Futbol Argentino",
        "bra": "Brasileirão",
        "ucl": "UEFA Champions League",
        "uel": "UEFA Europa League",
        "uecl": "UEFA Conference League",
        "epl": "Premier League",
        "laliga santander": "La Liga",
        "laliga ea sports": "La Liga",
        "serie a tim": "Serie A",
        "serie a italia": "Serie A",
        "copa lib": "Copa Libertadores",
        "copa sud": "Copa Sudamericana",
        "elim sudamericanas": "Eliminatorias Sudamericanas",
        "wcq": "Eliminatorias Mundial",
        "wc qual": "Eliminatorias Mundial",
        "concacaf chamnpions cup": "Concacaf Champions Cup",
        "copa de campeones de la concacaf": "Concacaf Champions Cup",
        "serie a bresil": "Brasileirao",
        "campeonato brasileno de serie a": "Brasileirao",
        "hockey men ice hockey winter olympics": "Hockey Hielo Juegos Olímpicos",
    }
    
    text = liga.lower().strip()
    for key, value in normalizaciones.items():
        if key in text:
            return value
    
    # Capitalizar cada palabra si no encontramos normalización
    return " ".join(word.capitalize() for word in liga.split())


def build_event(
    dt_arg: datetime,
    logo: str,
    liga: str,
    equipos: str,
    canales: List[Dict[str, Any]],
    date_offset: int,
    use_chatgpt: bool = USE_CHATGPT,
) -> Dict[str, Any]:
    dt_utc = dt_arg + timedelta(hours=3)
    
    # Reparar encoding roto en liga y equipos
    liga = fix_encoding(liga)
    equipos = fix_encoding(equipos)
    
    # Normalizar nombre de liga
    liga_normalizada = normalize_liga_name(liga)
    
    # Variables para inferencia
    deporte = ""
    pais = ""
    chatgpt_info: Dict[str, str] = {}
    
    # PASO 1: Si no hay liga, intentar inferir del mapa de equipos (sin costo)
    if not liga_normalizada and equipos:
        liga_inferida = infer_liga_from_equipos(equipos)
        if liga_inferida:
            liga_normalizada = liga_inferida
            logger.debug("Liga inferida de equipos: %s -> %s", equipos, liga_normalizada)
    
    # PASO 2: Si no hay liga o no podemos inferir país, consultar ChatGPT (controlado por USE_CHATGPT)
    needs_pais = not infer_pais(liga_normalizada) if liga_normalizada else True
    if use_chatgpt and equipos and (not liga_normalizada or needs_pais):
        chatgpt_info = query_chatgpt_for_match_info(equipos, liga_normalizada or liga)
        if chatgpt_info:
            if not liga_normalizada and chatgpt_info.get("liga"):
                liga_normalizada = chatgpt_info.get("liga", "")
            if not deporte and chatgpt_info.get("deporte"):
                deporte = chatgpt_info.get("deporte", "")
            if not pais and chatgpt_info.get("pais"):
                pais = chatgpt_info.get("pais", "")
    
    # Inferir logo si no hay uno proporcionado
    logo_final = logo or infer_logo(liga_normalizada, equipos)
    
    # Inferir deporte si no lo tenemos de ChatGPT
    if not deporte:
        deporte = infer_deporte(liga_normalizada, equipos)
    
    # Inferir país si no lo tenemos de ChatGPT
    if not pais:
        pais = infer_pais(liga_normalizada)
    
    # Si seguimos sin liga, usar el texto de equipos como liga para no dejarla vacía
    if not liga_normalizada:
        liga_normalizada = equipos or ""

    return {
        "hora_utc": format_utc(dt_utc),
        "hora_argentina": format_argentina(dt_arg),
        "logo": logo_final,
        "liga": liga_normalizada,
        "equipos": equipos or "",
        "deporte": deporte,
        "pais": pais,
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


def fix_encoding(text: str) -> str:
    """Intenta reparar texto con encoding roto (mojibake / replacement chars)."""
    if not text:
        return text
    # Paso 1: Intentar arreglar mojibake típico latin1→utf8
    # (ej: "ï¿½" son los bytes EF BF BD de U+FFFD leídos como latin-1)
    try:
        fixed = text.encode('latin-1').decode('utf-8')
        if fixed != text:
            text = fixed  # NO retornar aún, continuar con correcciones
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    # Paso 2: Si tiene U+FFFD (replacement character), aplicar correcciones conocidas
    if '\ufffd' in text:
        correcciones = {
            "K\ufffdbenhavn": "København",
            "Nordsj\ufffdlland": "Nordsjælland",
            "Vara\ufffddin": "Varaždin",
            "Alav\ufffds": "Alavés",
            "Vit\ufffdria Guimar\ufffdes": "Vitória Guimarães",
            "\ufffdeleznicar": "Železnicar",
            "M\ufffdnchen": "München",
            "Atl\ufffdtico": "Atlético",
            "Ath Bilba\ufffd": "Ath Bilbaó",
            "C\ufffdceres": "Cáceres",
            "G\ufffdteborg": "Göteborg",
            "Malm\ufffd": "Malmö",
            "Boras\ufffd": "Borås",
            "S\ufffdnderjyskE": "SønderjyskE",
            "Br\ufffdndby": "Brøndby",
            "\ufffdrebro": "Örebro",
            "Laktasi": "Laktaši",
            "Famos-SA\ufffdK": "Famos-SAIK",
            "Posusje": "Posušje",
            "Siroki": "Široki",
            "Velez": "Velež",
            "Zeljeznicar": "Željezničar",
        }
        for bad, good in correcciones.items():
            if bad in text:
                text = text.replace(bad, good)
    return text


def fetch_html(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=TIMEOUT_SEC)
    # Detectar encoding real en lugar de forzar utf-8
    if response.apparent_encoding:
        response.encoding = response.apparent_encoding
    else:
        response.encoding = "utf-8"
    text = response.text
    # Si aún hay caracteres rotos, intentar con latin-1
    if '\ufffd' in text or '�' in text:
        try:
            text = response.content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = response.content.decode('latin-1')
            except Exception:
                pass
    return text


def parse_elcanaldeportivo(session: requests.Session) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        response = session.get(ELCANALDEPORTIVO_URL, timeout=TIMEOUT_SEC)
        # Decodificar con el encoding correcto (la fuente puede ser latin-1)
        try:
            data = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                data = json.loads(response.content.decode("latin-1"))
            except Exception:
                response.encoding = response.apparent_encoding or "utf-8"
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
            flag_src = flag_img.get("src", "").strip()
            if flag_src.startswith("http://") or flag_src.startswith("https://"):
                logo = flag_src
            elif flag_src.startswith("//"):
                logo = "https:" + flag_src
            else:
                logo = make_abs_url("https://tvtvhd.com/", flag_src)

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
    # Intentar primero la nueva agenda JSON (fuente oficial del sitio)
    try:
        resp = session.get(TVTVHD_JSON_URL, timeout=TIMEOUT_SEC)
        data = resp.json()
    except Exception as exc:
        logger.error("tvtvhd json error: %s", exc)
        data = None

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        for item in data.get("data", []):
            attr = item.get("attributes", {}) if isinstance(item, dict) else {}
            date_str = attr.get("date_diary") or ""
            time_str = (attr.get("diary_hour") or "").strip()
            desc = normalize_ws(attr.get("diary_description") or "")
            if not date_str or not time_str:
                continue

            dt_source: Optional[datetime] = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    dt_source = datetime.strptime(f"{date_str} {time_str}", fmt)
                    break
                except Exception:
                    continue
            if not dt_source:
                continue

            # Horario fuente usa America/Lima (UTC-5). Convertir a Argentina (UTC-3).
            dt_arg = dt_source + timedelta(hours=2)
            date_offset = (dt_arg.date() - dt_source.date()).days

            liga, equipos = parse_league_and_teams(desc)
            logo = ""
            canales: List[Dict[str, Any]] = []

            embeds = attr.get("embeds", {}) if isinstance(attr, dict) else {}
            if isinstance(embeds, dict):
                for embed in embeds.get("data", []) or []:
                    embed_attr = embed.get("attributes", {}) if isinstance(embed, dict) else {}
                    label = normalize_ws(embed_attr.get("embed_name") or "TVTVHD")
                    iframe = embed_attr.get("embed_iframe") or ""
                    url = make_abs_url("https://tvtvhd.com/", iframe)

                    parsed = urlparse(iframe) if iframe else None
                    decoded = ""
                    if parsed and parsed.query:
                        qs = parse_qs(parsed.query)
                        decoded = decode_base64(qs.get("r", [""])[0])
                    if decoded:
                        url = decoded
                    canales.append({"nombre": label, "url": url, "calidad": ""})

            if not canales:
                canales.append({"nombre": "TVTVHD", "url": "", "calidad": ""})

            events.append(build_event(dt_arg, logo, liga, equipos, canales, date_offset))

        if events:
            return events

    # Fallback a parseo HTML antiguo por si la API JSON falla
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


def canonical_equipos_key(equipos: str) -> str:
    """Genera una clave canónica de equipos para detectar duplicados aunque varíe el separador."""
    if not equipos:
        return ""
    txt = equipos
    # Unificar separadores habituales
    txt = re.sub(r"\s+[-–—:]\s+", " vs ", txt)
    txt = re.sub(r"\s+v\s+", " vs ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s+vs?\.?\s+", " vs ", txt, flags=re.IGNORECASE)
    parts = [p.strip() for p in txt.split(" vs ") if p.strip()]

    def normalize_team_token(token: str) -> str:
        t = normalize_text(token)
        aliases = {
            "ettifaq": "ittifaq",
            "etifaq": "ittifaq",
            "etifak": "ittifaq",
            "alittifaq": "alittifaq",
            "alettifaq": "alittifaq",
            "aletifaq": "alittifaq",
        }
        for src, dst in aliases.items():
            if src in t:
                t = t.replace(src, dst)
        return t

    parts = [normalize_team_token(p) for p in parts]
    if len(parts) >= 2:
        parts = sorted(parts)
        txt = " vs ".join(parts)
    return normalize_text(txt)


def event_key(event: Dict[str, Any]) -> Tuple[str, str]:
    """
    Genera una clave única para identificar eventos duplicados.
    Usa equipos normalizados + hora UTC (redondeada a 15 min).
    """
    equipos = canonical_equipos_key(event.get("equipos", ""))
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

    def choose_liga(existing_liga: str, new_liga: str, equipos: str) -> str:
        """Elige la liga preferida entre dos opciones.
        Prioridad: que tenga logo canónico disponible; luego la más descriptiva (más larga)."""
        if not new_liga:
            return existing_liga
        if not existing_liga:
            return new_liga

        existing_logo_canonical = infer_logo(existing_liga, equipos)
        new_logo_canonical = infer_logo(new_liga, equipos)

        if new_logo_canonical and not existing_logo_canonical:
            return new_liga
        if existing_logo_canonical and not new_logo_canonical:
            return existing_liga

        # Si ambos tienen/ no tienen logo canónico, elegir la más larga (más info)
        if len(new_liga) > len(existing_liga):
            return new_liga
        return existing_liga
    
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

            # Elegir la mejor liga
            chosen_liga = choose_liga(existing.get("liga", ""), event.get("liga", ""), existing.get("equipos", ""))
            existing["liga"] = chosen_liga

            # Logo: preferir el canónico de la liga elegida; si no, mantener existente o nuevo si estaba vacío
            logo_existing = existing.get("logo", "")
            logo_new = event.get("logo", "")
            canonical_logo = infer_logo(chosen_liga, existing.get("equipos", "")) if chosen_liga else ""
            if canonical_logo:
                existing["logo"] = canonical_logo
            elif not logo_existing and logo_new:
                existing["logo"] = logo_new

            # Deporte
            if not existing.get("deporte") and event.get("deporte"):
                existing["deporte"] = event["deporte"]
            
            # País
            if not existing.get("pais") and event.get("pais"):
                existing["pais"] = event["pais"]
        else:
            # Nuevo evento, clonar para evitar modificar el original
            merged[key] = {
                "hora_utc": event.get("hora_utc", ""),
                "hora_argentina": event.get("hora_argentina", ""),
                "logo": event.get("logo", ""),
                "liga": event.get("liga", ""),
                "equipos": event.get("equipos", ""),
                "deporte": event.get("deporte", ""),
                "pais": event.get("pais", ""),
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
    sources = [
        ("elcanaldeportivo", parse_elcanaldeportivo),
        ("streamx10", parse_streamx10),
        ("bolaloca", parse_bolaloca),
        ("antenasport", parse_antenasport),
        ("pirlotvoficial", parse_pirlotvoficial),
        ("tvlibree", parse_tvlibree),
        ("tvtvhd", parse_tvtvhd),
    ]

    for name, parser_fn in sources:
        try:
            parsed = parser_fn(session)
        except Exception as exc:
            logger.error("%s parser error: %s", name, exc)
            parsed = []
        logger.info("%s: %d eventos", name, len(parsed))
        all_events.extend(parsed)

    # Deduplicar y fusionar canales de eventos iguales
    logger.info("Eventos antes de deduplicar: %d", len(all_events))
    all_events = merge_events(all_events)
    logger.info("Eventos después de deduplicar: %d", len(all_events))

    all_events.sort(key=lambda x: x.get("hora_utc", ""))

    # Normalizar logos: misma liga = mismo logo (usa LIGA_LOGOS como fuente de verdad)
    all_events = normalize_logos_by_liga(all_events)

    return all_events


def normalize_logos_by_liga(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Asegura que todos los eventos de la misma liga usen el mismo logo.
    Prioridad: logo de LIGA_LOGOS > logo más frecuente entre los eventos.
    """
    from collections import Counter

    # Paso 1: Para cada liga, determinar el logo correcto
    liga_logo_counts: Dict[str, Counter] = {}
    for ev in events:
        liga = ev.get("liga", "").strip()
        logo = ev.get("logo", "").strip()
        if liga and logo:
            if liga not in liga_logo_counts:
                liga_logo_counts[liga] = Counter()
            liga_logo_counts[liga][logo] += 1

    # Paso 2: Para cada liga, elegir el logo correcto
    liga_logo_final: Dict[str, str] = {}
    for liga, logo_counts in liga_logo_counts.items():
        # Primero intentar con LIGA_LOGOS (fuente de verdad)
        canonical = infer_logo(liga, "")
        if canonical:
            liga_logo_final[liga] = canonical
        else:
            # Usar el logo más frecuente
            liga_logo_final[liga] = logo_counts.most_common(1)[0][0]

    # Paso 3: Aplicar logo normalizado solo si el evento no tiene logo (prioriza fuente original)
    changed = 0
    for ev in events:
        liga = ev.get("liga", "").strip()
        if liga and liga in liga_logo_final:
            old_logo = ev.get("logo", "")
            if old_logo:
                continue
            new_logo = liga_logo_final[liga]
            ev["logo"] = new_logo
            changed += 1

    if changed:
        logger.info("Logos normalizados (solo vacios): %d eventos actualizados", changed)

    return events


def sync_to_github(json_path: Path) -> None:
    """Sube partidos.json a GitHub via API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    owner = "frandev2024-svg"
    repo = "scrappersdata"
    branch = "main"
    github_file = "partidos.json"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_file}"

        # Obtener SHA si ya existe
        r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
        sha = r.json().get("sha") if r.status_code == 200 else None

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "message": f"Actualizar {github_file} - {timestamp}",
            "content": content_b64,
            "branch": branch
        }
        if sha:
            data["sha"] = sha

        r = requests.put(url, headers=headers, json=data, timeout=120)
        if r.status_code in [200, 201]:
            commit = r.json()["commit"]["sha"][:7]
            logger.info("GitHub: subida exitosa (commit %s)", commit)
        else:
            logger.error("GitHub: error %s - %s", r.status_code, r.json().get("message", ""))
    except Exception as e:
        logger.error("Error subiendo a GitHub: %s", e)


def filtrar_eventos_pasados(events: list) -> list:
    """Elimina eventos cuya hora UTC ya pasó (más de 4 horas de margen)."""
    ahora = datetime.now(timezone.utc)
    margen = timedelta(hours=4)  # Mantener partidos que empezaron hace menos de 4h
    filtrados = []
    for ev in events:
        hora_str = ev.get("hora_utc", "")
        if not hora_str:
            filtrados.append(ev)
            continue
        try:
            hora_ev = datetime.fromisoformat(hora_str.replace("Z", "+00:00"))
            if hora_ev + margen >= ahora:
                filtrados.append(ev)
        except Exception:
            filtrados.append(ev)  # Si no se puede parsear, mantener
    return filtrados


def main() -> None:
    # Cargar caché de ChatGPT
    load_chatgpt_cache()
    
    # Obtener todos los eventos
    events = build_all_events()
    # Filtrar eventos pasados
    antes = len(events)
    events = filtrar_eventos_pasados(events)
    logger.info("Eventos filtrados: %d -> %d (eliminados %d pasados)", antes, len(events), antes - len(events))
    
    # Guardar JSON
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    logger.info("Eventos guardados: %s", len(events))
    
    # Guardar caché de ChatGPT
    save_chatgpt_cache()
    
    # Subir a GitHub
    sync_to_github(OUTPUT_JSON)


if __name__ == "__main__":
    main()
