# Partidos M3U8 — Documentación de dominios y reproducción

## Resumen general

El archivo `partidos.json` contiene **296 partidos** con **846 canales** que tienen URLs m3u8 funcionales extraídas de 7 tipos de servidores diferentes.

---

## Dominios y cómo reproducir cada uno

### 1. `sdfgsdfg.sbs` — Antenasport + Miatvhd (441 canales)

**Ejemplo:**
```
https://max2new.sdfgsdfg.sbs/max2/primasky4nz/mono.m3u8
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO |
| Token/Expiración | NO — enlaces permanentes |
| Header Referer | NO |
| Reproducción | Directa, sin nada especial |

**Subdominios conocidos:** `max2new`, `nfsnew`, `wikinew`, `top1new`, `top2new`, `x4new`, `dokko1new`

**Cómo reproducir:**
Simplemente abrir la URL en cualquier reproductor HLS (VLC, ExoPlayer, hls.js, Clappr, etc.). No necesita headers ni tokens.

---

### 2. `fubohd.com` — TVtvHD (95 canales)

**Ejemplo:**
```
https://anvtcax.fubohd.com:443/espn/mono.m3u8?token=c293a18a8c700e96...
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO para extraer |
| Token | SÍ — `?token=HASH-XX-TIMESTAMP-TIMESTAMP` |
| Expiración | SÍ (implícita en el token) |
| DNS efímero | **SÍ** — los subdominios son aleatorios y dejan de resolver en minutos |
| Header Referer | NO |
| Reproducción | **Muy difícil** — los subdominios DNS son efímeros |

**Problema principal:** Los subdominios (`anvtcax`, `rm8zcvk3`, `agvyby`, etc.) son generados dinámicamente y dejan de existir rápidamente. Los links guardados van a fallar con error DNS.

**Cómo reproducir:**
Habría que re-extraer la URL justo en el momento de reproducir. No sirve guardarlas.

---

### 3. `58103793.net` / `77911050.net` — Bolaloca vía doubttooth/fibretower (~178 canales)

**Ejemplo:**
```
https://k7h2hupk.58103793.net:8443/hls/6d8sd4.m3u8?s=lDaEDcwnSn8X...&e=1771624963
https://6zewy2uk.77911050.net:8443/hls/a2ao4jza74qn.m3u8?s=zjoQ7RT...&e=1771624962
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO (extraíble con Python) |
| Token | SÍ — `?s=HASH&e=UNIX_TIMESTAMP` |
| Expiración | SÍ — parámetro `e` es Unix timestamp, duración ~5-6 horas |
| Header Referer | **SÍ** |
| Reproducción | Con header Referer correcto |

**Headers necesarios:**
```
Referer: https://doubttooth.net/
```
o (para los de fibretower):
```
Referer: https://fibretower.net/
```

**Cómo reproducir:**
Configurar el header `Referer` en el reproductor. En ExoPlayer/Android se puede setear con `DefaultHttpDataSource.Factory().setDefaultRequestProperties()`. Si el link expiró (status 403), hay que re-extraer desde la URL original de bolaloca.

---

### 4. `sanwalyaarpya.com` — Bolaloca vía hoca6 (~89 canales)

**Ejemplo:**
```
https://n4.sanwalyaarpya.com:1686/hls/wsmkmlfeed151.m3u8?md5=LNgwL2sa6w...&expires=1771610562
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO (extraíble con Python) |
| Token | SÍ — `?md5=HASH&expires=UNIX_TIMESTAMP` |
| Expiración | SÍ — `expires` es Unix timestamp, duración ~2-4 horas |
| Subdominio rotativo | SÍ — `n1` a `n9` rotan en cada request |
| Header Referer | **SÍ** |
| Reproducción | Con header Referer correcto |

**Headers necesarios:**
```
Referer: https://hoca6.com/
```

**Cómo reproducir:**
Igual que los de doubttooth — necesita header `Referer`. Los links expiran más rápido (~2-4 horas). Re-extraer si devuelve 403/404.

---

### 5. `marsrivagg.click` — Streamx10 (39 canales)

**Ejemplo:**
```
https://ssout.marsrivagg.click:443/global/hyper1/index.m3u8?token=c92e82627c...
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO |
| Token | SÍ — `?token=HASH-XX-TIMESTAMP` |
| Expiración | SÍ (~24 horas) |
| Header Referer | NO |
| Reproducción | Directa — sin headers especiales |

**Cómo reproducir:**
Abrir directamente en cualquier reproductor HLS. No necesita headers. Si expiró, re-extraer desde la URL original.

---

### 6. `envivoslatam.org` — Streamtp10 (2 canales)

**Ejemplo:**
```
https://pvtn5y.envivoslatam.org:443/hotflix/espn/index.m3u8?token=852246a479...
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO |
| Token | SÍ — `?token=HASH-XX-TIMESTAMP` |
| Expiración | SÍ (~24 horas) |
| Header Referer | NO |
| Reproducción | Directa — sin headers especiales |

**Cómo reproducir:**
Igual que streamx10. Abrir directamente.

---

### 7. `smarthard.click` — Welivesports (1 canal)

**Ejemplo:**
```
https://smarthard.click/hls/sabrouchfoxsp1arg/index.m3u8?st=TEDhMt3azhCfs...&e=1771614153
```

| Propiedad | Valor |
|-----------|-------|
| Requiere JS | NO |
| Token | SÍ — `?st=HASH&e=UNIX_TIMESTAMP` |
| Expiración | SÍ |
| Header Referer | **SÍ** |
| Reproducción | Con header Referer correcto |

**Headers necesarios:**
```
Referer: https://obstream.pro/
```

---

## Tabla resumen

| Servidor | Canales | Token | Expira | Referer necesario | Reproducción |
|----------|---------|-------|--------|-------------------|-------------|
| `sdfgsdfg.sbs` | 441 | NO | NO | NO | ✅ Directo |
| `fubohd.com` | 95 | SÍ | SÍ (DNS) | NO | ❌ DNS efímero |
| `58103793/77911050.net` | ~178 | SÍ | ~5h | `doubttooth.net` / `fibretower.net` | ⚠️ Con Referer |
| `sanwalyaarpya.com` | ~89 | SÍ | ~2-4h | `hoca6.com` | ⚠️ Con Referer |
| `marsrivagg.click` | 39 | SÍ | ~24h | NO | ✅ Directo |
| `envivoslatam.org` | 2 | SÍ | ~24h | NO | ✅ Directo |
| `smarthard.click` | 1 | SÍ | SÍ | `obstream.pro` | ⚠️ Con Referer |

---

## Dominios que NO se pudieron extraer

| Dominio origen | Canales | Razón |
|----------------|---------|-------|
| `elcanaldeportivo.com` | 38 | Requiere ejecución JavaScript real. La API de deepcathink.com devuelve siempre `ch=spn` como placeholder; el m3u8 real se genera en el cliente con JS. |
| `tvlibree.com` | 2 | Carga iframes dinámicamente con JavaScript. No hay src estático extraíble. |
| `nebunexa.life` | 1 | Requiere una extensión de Chrome para funcionar. No se puede extraer con Python. |

---

## Cómo re-extraer links expirados

Para dominios con token de expiración, ejecutar:

```bash
python process_partidos_m3u8.py
```

El script:
1. Lee `partidos.json` (o restaurar desde `partidos_backup_before_m3u8.json`)
2. Extrae m3u8 de cada URL original en paralelo (8 workers)
3. Elimina canales sin m3u8 y partidos sin canales
4. Guarda el resultado en `partidos.json`

---

## Ejemplo de uso en reproductor

### Sin headers (sdfgsdfg.sbs, marsrivagg, envivoslatam)
```javascript
// hls.js
var hls = new Hls();
hls.loadSource('https://max2new.sdfgsdfg.sbs/max2/primasky4nz/mono.m3u8');
hls.attachMedia(video);
```

### Con Referer (doubttooth, fibretower, hoca6, smarthard)
```javascript
// hls.js con xhrSetup para Referer
var hls = new Hls({
  xhrSetup: function(xhr) {
    xhr.setRequestHeader('Referer', 'https://doubttooth.net/');
  }
});
hls.loadSource('https://k7h2hupk.58103793.net:8443/hls/6d8sd4.m3u8?s=xxx&e=xxx');
hls.attachMedia(video);
```

### Android ExoPlayer
```kotlin
val dataSourceFactory = DefaultHttpDataSource.Factory()
    .setDefaultRequestProperties(mapOf("Referer" to "https://doubttooth.net/"))
val mediaItem = MediaItem.fromUri(m3u8Url)
player.setMediaItem(mediaItem)
```

### VLC (línea de comandos)
```bash
vlc "https://max2new.sdfgsdfg.sbs/max2/primasky4nz/mono.m3u8"

# Con Referer:
vlc --http-referrer="https://doubttooth.net/" "https://k7h2hupk.58103793.net:8443/hls/xxx.m3u8?s=xxx&e=xxx"
```
