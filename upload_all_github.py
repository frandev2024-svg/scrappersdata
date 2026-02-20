#!/usr/bin/env python3
"""
Script para subir todos los JSON a GitHub.
Sube: peliculas.json, series.json, anime.json, anime2.json, episodios_recientes.json, canales.json
"""

import json
import base64
import requests
import os
import sys
from datetime import datetime

# ============== CONFIGURACIÓN ==============
# Se requiere GITHUB_TOKEN en variables de entorno/secretos
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = "frandev2024-svg"
GITHUB_REPO = "scrappersdata"
GITHUB_BRANCH = "main"

# Archivos a subir (local -> github)
ARCHIVOS = [
    {"local": "peliculas.json",          "github": "peliculas.json"},
    {"local": "series.json",             "github": "series.json"},
    {"local": "anime.json",              "github": "anime.json"},
    {"local": "anime2.json",             "github": "anime2.json"},
    {"local": "episodios_recientes.json", "github": "episodios_recientes.json"},
    {"local": "canales.json",            "github": "canales.json"},
    {"local": "partidos.json",           "github": "partidos.json"},
]
# ===========================================


def get_file_sha(owner, repo, path, branch, token):
    """Obtiene el SHA del archivo si ya existe en el repositorio."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers, params={"ref": branch})
    if response.status_code == 200:
        return response.json().get("sha")
    return None


def upload_file(local_path, github_path, owner, repo, branch, token):
    """Sube o actualiza un archivo en GitHub."""
    if not os.path.exists(local_path):
        return "NO_EXISTE"

    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    size_mb = len(content.encode("utf-8")) / (1024 * 1024)
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    sha = get_file_sha(owner, repo, github_path, branch, token)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"Actualizar {github_path} - {timestamp}",
        "content": content_b64,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)

    if response.status_code in [200, 201]:
        commit = response.json()["commit"]["sha"][:7]
        return f"OK|{size_mb:.1f}MB|{commit}"
    else:
        msg = response.json().get("message", str(response.status_code))
        return f"ERROR|{msg}"


def main():
    print("=" * 55)
    print("   SUBIDOR DE JSON A GITHUB")
    print(f"   Repo: {GITHUB_OWNER}/{GITHUB_REPO}")
    print("=" * 55)

    if not GITHUB_TOKEN or GITHUB_TOKEN == "TU_TOKEN_AQUI":
        print("\nError: Configura GITHUB_TOKEN primero.")
        sys.exit(1)

    # Permitir elegir archivos específicos por argumento
    # Ej: python upload_all_github.py anime2 canales
    if len(sys.argv) > 1:
        filtros = [a.lower() for a in sys.argv[1:]]
        archivos = [a for a in ARCHIVOS if any(f in a["local"].lower() for f in filtros)]
        if not archivos:
            print(f"\nNo se encontraron archivos que coincidan con: {', '.join(filtros)}")
            print(f"Disponibles: {', '.join(a['local'] for a in ARCHIVOS)}")
            sys.exit(1)
    else:
        archivos = ARCHIVOS

    print(f"\nArchivos a subir: {len(archivos)}")
    for a in archivos:
        existe = "OK" if os.path.exists(a["local"]) else "NO EXISTE"
        print(f"  - {a['local']} [{existe}]")

    print()
    exitosos = 0
    fallidos = 0
    saltados = 0

    for i, archivo in enumerate(archivos, 1):
        local = archivo["local"]
        github = archivo["github"]
        print(f"[{i}/{len(archivos)}] Subiendo {local}...", end=" ", flush=True)

        result = upload_file(local, github, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN)

        if result == "NO_EXISTE":
            print(f"SALTADO (no existe)")
            saltados += 1
        elif result.startswith("OK"):
            parts = result.split("|")
            print(f"OK ({parts[1]}, commit {parts[2]})")
            exitosos += 1
        else:
            parts = result.split("|", 1)
            print(f"ERROR: {parts[1] if len(parts) > 1 else result}")
            fallidos += 1

    print(f"\n{'=' * 55}")
    print(f"  RESULTADO: {exitosos} subidos, {saltados} saltados, {fallidos} fallidos")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
