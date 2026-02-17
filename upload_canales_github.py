#!/usr/bin/env python3
"""
Script para subir canales.json a GitHub
Utiliza la API de GitHub para crear o actualizar el archivo en un repositorio.
"""

import json
import base64
import requests
import os
from datetime import datetime

# ============== CONFIGURACIÓN ==============
# Token de acceso personal de GitHub (con permisos 'repo'). Debe venir de entorno/secret.
# Crea uno en: https://github.com/settings/tokens si no usas el GITHUB_TOKEN automático de Actions.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Nombre de usuario u organización de GitHub
GITHUB_OWNER = "frandev2024-svg"

# Nombre del repositorio
GITHUB_REPO = "scrappersdata"

# Ruta del archivo en el repositorio (ej: "data/canales.json" o solo "canales.json")
GITHUB_FILE_PATH = "canales.json"

# Rama donde subir (normalmente "main" o "master")
GITHUB_BRANCH = "main"

# Archivo local a subir
LOCAL_FILE = "canales.json"
# ===========================================


def get_file_sha(owner, repo, path, branch, token):
    """Obtiene el SHA del archivo si ya existe en el repositorio."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    params = {"ref": branch}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json().get("sha")
    elif response.status_code == 404:
        return None
    else:
        print(f"Error al verificar archivo existente: {response.status_code}")
        print(response.json())
        return None


def upload_to_github(file_path, owner, repo, github_path, branch, token, commit_message=None):
    """Sube o actualiza un archivo en GitHub."""
    
    # Leer el archivo local
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{file_path}'")
        return False
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return False
    
    # Codificar contenido en base64
    content_bytes = content.encode("utf-8")
    content_base64 = base64.b64encode(content_bytes).decode("utf-8")
    
    # Mensaje de commit por defecto
    if not commit_message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Actualizar {github_path} - {timestamp}"
    
    # Verificar si el archivo ya existe para obtener su SHA
    sha = get_file_sha(owner, repo, github_path, branch, token)
    
    # Preparar la solicitud
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "message": commit_message,
        "content": content_base64,
        "branch": branch
    }
    
    if sha:
        data["sha"] = sha
        print(f"Archivo existente detectado. Actualizando...")
    else:
        print(f"Creando nuevo archivo...")
    
    # Realizar la solicitud PUT
    response = requests.put(url, headers=headers, json=data)
    
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"\n{'='*50}")
        print(f"SUBIDA EXITOSA!")
        print(f"{'='*50}")
        print(f"Archivo: {github_path}")
        print(f"Repositorio: {owner}/{repo}")
        print(f"Rama: {branch}")
        print(f"Commit: {result['commit']['sha'][:7]}")
        print(f"URL: {result['content']['html_url']}")
        print(f"{'='*50}")
        return True
    elif response.status_code == 403:
        print(f"\nError 403: Sin permisos de escritura")
        print(f"\nTu token 'fine-grained' necesita permisos adicionales.")
        print(f"\nPara solucionarlo:")
        print(f"1. Ve a: https://github.com/settings/tokens")
        print(f"2. Edita tu token o crea uno nuevo")
        print(f"3. En 'Repository access', selecciona el repo '{repo}'")
        print(f"4. En 'Permissions' -> 'Repository permissions':")
        print(f"   - Contents: Read and Write")
        print(f"5. Guarda y copia el nuevo token")
        print(f"\nO usa un token CLÁSICO con permiso 'repo' (más fácil):")
        print(f"https://github.com/settings/tokens/new?scopes=repo")
        return False
    else:
        print(f"\nError al subir archivo: {response.status_code}")
        print(response.json())
        return False


def validate_config():
    """Valida que la configuración esté completa."""
    errors = []
    
    if GITHUB_TOKEN == "TU_TOKEN_AQUI" or not GITHUB_TOKEN:
        errors.append("- GITHUB_TOKEN: Debes configurar tu token de acceso personal")
    
    if GITHUB_OWNER == "TU_USUARIO":
        errors.append("- GITHUB_OWNER: Debes configurar tu nombre de usuario de GitHub")
    
    if GITHUB_REPO == "TU_REPOSITORIO":
        errors.append("- GITHUB_REPO: Debes configurar el nombre del repositorio")
    
    if not os.path.exists(LOCAL_FILE):
        errors.append(f"- LOCAL_FILE: No se encontró el archivo '{LOCAL_FILE}'")
    
    return errors


def show_stats():
    """Muestra estadísticas del archivo a subir."""
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"\nEstadísticas de {LOCAL_FILE}:")
            print(f"  - Total de canales: {len(data)}")
            
            # Contar por categoría
            categories = {}
            for channel in data:
                cat = channel.get("category", "Sin categoría")
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"  - Categorías: {len(categories)}")
            print(f"\n  Top 5 categorías:")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5]:
                print(f"    • {cat}: {count} canales")
            print()
        except Exception as e:
            print(f"Error al leer estadísticas: {e}")


def main():
    print("=" * 50)
    print("   SUBIDOR DE CANALES A GITHUB")
    print("=" * 50)
    
    # Validar configuración
    errors = validate_config()
    if errors:
        print("\n⚠️  CONFIGURACIÓN INCOMPLETA:")
        print("\n".join(errors))
        print("\nEdita este archivo y configura las variables al inicio.")
        print("\nPara crear un token de GitHub:")
        print("1. Ve a https://github.com/settings/tokens")
        print("2. Crea un nuevo token con permisos 'repo'")
        print("3. Copia el token y pégalo en GITHUB_TOKEN")
        return
    
    # Mostrar estadísticas
    show_stats()
    
    # Subir archivo
    print(f"Subiendo {LOCAL_FILE} a GitHub...")
    success = upload_to_github(
        file_path=LOCAL_FILE,
        owner=GITHUB_OWNER,
        repo=GITHUB_REPO,
        github_path=GITHUB_FILE_PATH,
        branch=GITHUB_BRANCH,
        token=GITHUB_TOKEN
    )
    
    if not success:
        print("\nLa subida falló. Revisa los errores anteriores.")


if __name__ == "__main__":
    main()
