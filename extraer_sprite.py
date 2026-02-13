import json
import re
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image

SPRITE_URL = "https://pirlotvoficial.com/img/banderas.png"
RAW_BASE_URL = "https://raw.githubusercontent.com/frandev2024-svg/scrappersdata/main/pirlotv_icons/"

CSS_SNIPPET = """
.ad{background-position:0 0}.ae{background-position:-18px 0}.arg{background-position:-36px 0}.at{background-position:-54px 0}.au{background-position:-72px 0}.be{background-position:-90px 0}.bg{background-position:-108px 0}.bo{background-position:-126px 0}.by{background-position:-144px 0}.br{background-position:-162px 0}.ca{background-position:-180px 0}.cl{background-position:-198px 0}.cn{background-position:-216px 0}.co{background-position:0 -12px}.cr{background-position:-18px -12px}.cz{background-position:-36px -12px}.de{background-position:-54px -12px}.dk{background-position:-72px -12px}.do{background-position:-90px -12px}.dz{background-position:-108px -12px}.ec{background-position:-126px -12px}.eg{background-position:-144px -12px}.en{background-position:-162px -12px}.es{background-position:-180px -12px}.eu{background-position:-198px -12px}.fi{background-position:-216px -12px}.fr{background-position:0 -24px}.gb{background-position:-18px -24px}.gr{background-position:-36px -24px}.gt{background-position:-54px -24px}.hn{background-position:-72px -24px}.hr{background-position:-90px -24px}.hu{background-position:-108px -24px}.ie{background-position:-126px -24px}.il{background-position:-144px -24px}.in{background-position:-162px -24px}.is{background-position:-180px -24px}.it{background-position:-198px -24px}.jp{background-position:-216px -24px}.kr{background-position:0 -36px}.lu{background-position:-18px -36px}.mx{background-position:-36px -36px}.ni{background-position:-54px -36px}.nl{background-position:-72px -36px}.no{background-position:-90px -36px}.nz{background-position:-108px -36px}.pa{background-position:-126px -36px}.pe{background-position:-144px -36px}.pl{background-position:-162px -36px}.pr{background-position:-180px -36px}.pt{background-position:-198px -36px}.py{background-position:-216px -36px}.qa{background-position:0 -48px}.ro{background-position:-18px -48px}.rs{background-position:-36px -48px}.ru{background-position:-54px -48px}.sa{background-position:-72px -48px}.se{background-position:-90px -48px}.sk{background-position:-108px -48px}.sv{background-position:-126px -48px}.su{background-position:-144px -48px}.th{background-position:-162px -48px}.tj{background-position:-180px -48px}.tr{background-position:-198px -48px}.tt{background-position:-216px -48px}.us{background-position:0 -60px}.uy{background-position:-18px -60px}.ve{background-position:-36px -60px}.uefanl{background-position:-54px -60px}.mun{background-position:-72px -60px}.fifa{background-position:-90px -60px}.oli{background-position:-108px -60px}.toro{background-position:-126px -60px}.ufc{background-position:-144px -60px}.nazcar{background-position:-162px -60px}.motogp{background-position:-180px -60px}
.soccer{background-position:0 -83px}.bkb{background-position:-18px -83px}.voley{background-position:-36px -83px}.tenis{background-position:-54px -83px}.golf{background-position:-72px -83px}.snooker{background-position:-90px -83px}.mlb{background-position:-108px -83px}.el{background-position:-126px -83px}.ch{background-position:-144px -83px}.uefa{background-position:-162px -83px}.suda{background-position:-180px -83px}.concacaf{background-position:-198px -83px}.caf{background-position:-216px -83px}.eu21{background-position:0 -100px}.eu19{background-position:-18px -100px}.am{background-position:-36px -100px}.nfl{background-position:-54px -100px}.cfl{background-position:-72px -100px}.rugby{background-position:-90px -100px}.wwe{background-position:-108px -100px}.boxeo{background-position:-126px -100px}.dardos{background-position:-144px -100px}.mundial{background-position:-162px -100px}.euro{background-position:-180px -100px}.america{background-position:-198px -100px}.rfef{background-position:-216px -100px}.otros{background-position:0 -116px}.nba{background-position:-18px -116px}.nhl{background-position:-36px -116px}.ci{background-position:-54px -116px}.csuda{background-position:-72px -116px}.lib{background-position:-90px -116px}.uefacup{background-position:-108px -116px}.ms21{background-position:-126px -116px}.oro{background-position:-144px -116px}.icc{background-position:-162px -116px}.f1{background-position:-180px -116px}.beisbol{background-position:-198px -116px}
"""

SPORT_HEIGHT_CLASSES = {
    "am","america","beisbol","bkb","boxeo","caf","cfl","ch","ci","concacaf","csuda",
    "dardos","el","eu19","eu21","euro","f1","golf","icc","lib","mlb","ms21","mundial",
    "nba","nfl","nhl","oro","otros","rfef","rugby","snooker","soccer","suda","tenis",
    "uefa","uefacup","voley","wwe","motogp","ufc","nazcar","toro","oli","mun","uefanl"
}


def main() -> None:
    out_dir = Path("pirlotv_icons")
    out_dir.mkdir(exist_ok=True)

    sprite = Image.open(BytesIO(requests.get(SPRITE_URL, timeout=15).content)).convert("RGBA")

    pattern = re.compile(r"\.([a-z0-9]+)\{background-position:([-0-9]+)px ([-0-9]+)px\}")
    entries = pattern.findall(CSS_SNIPPET)
    for name, x_str, y_str in entries:
        x = abs(int(x_str))
        y = abs(int(y_str))
        w = 18
        h = 17 if name in SPORT_HEIGHT_CLASSES else 12
        box = (x, y, x + w, y + h)
        sprite.crop(box).save(out_dir / f"{name}.png")

    mapping = {name: f"{RAW_BASE_URL}{name}.png" for name, _, _ in entries}
    map_path = Path("pirlotv_icons_map.json")
    map_path.write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Saved {len(list(out_dir.iterdir()))} icons to {out_dir} and mapping to {map_path}")


if __name__ == "__main__":
    main()
