# Media Server Stack - Docker Compose

Stack completo de automatización de descargas y gestión de contenido multimedia usando Docker.

## ✨ Características Principales

- 🔗 **Sin Duplicación**: Usa hardlinks para evitar duplicar archivos (ahorra ~50% de espacio)
- 🤖 **Totalmente Automatizado**: Descarga, organiza y subtitula contenido automáticamente
- 📱 **Gestión Centralizada**: Un solo lugar para gestionar todos los servicios
- 🌍 **Subtítulos Múltiples**: Soporte para múltiples idiomas automáticamente
- 🐳 **Docker Native**: Fácil instalación y mantenimiento
- 🔒 **Seguro**: Configuración aislada con redes Docker

## 🎯 Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Sonarr** | 8989 | Gestión automática de series de TV |
| **Radarr** | 7878 | Gestión automática de películas |
| **Lidarr** | 8686 | Gestión automática de música |
| **Transmission** | 9091 | Cliente de descargas torrent |
| **Prowlarr** | 9696 | Gestión centralizada de indexers |
| **Plex** | 32400 | Media Server para reproducción |
| **Bazarr** | 6767 | Descarga automática de subtítulos |
| **Seerr** | 5055 | Gestión de peticiones (frontend tipo Netflix) |
| **Tautulli** | 8181 | Monitoreo y estadísticas de Plex |
| **Recyclarr** | — | Sincroniza perfiles/calidad de TRaSH Guides (cron) |

## 📋 Prerrequisitos

- **Sistema operativo**: Linux (probado en Raspberry Pi / ARM64 y x86_64).
- **Docker Engine** 20.10+ y el plugin **Docker Compose v2**:
  ```bash
  # Instalación rápida (Debian/Ubuntu/Raspberry Pi OS)
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"   # cierra sesión y vuelve a entrar
  docker compose version            # verifica que Compose v2 está disponible
  ```
- **git** para clonar el repositorio.
- **Espacio en disco** suficiente para tu biblioteca (las descargas y los hardlinks viven en `media/`).
- El **filesystem de `media/` debe soportar hardlinks** (ext4, xfs, btrfs…). Evita montar `downloads/` y `tv/` en volúmenes distintos: el hardlink solo funciona dentro del mismo filesystem.

## 📁 Estructura de Directorios

```
media-stack/
├── docker-compose.yml   # Definición de los 7 servicios
├── .env.example         # Plantilla de variables (PUID/PGID/TZ) → copiar a .env
├── .gitignore           # Excluye media/ y los config/ con secretos
├── README.md
├── sonarr/config/       # Config de Sonarr      (se crea sola al primer arranque)
├── radarr/config/       # Config de Radarr      (idem)
├── lidarr/config/       # Config de Lidarr      (idem)
├── transmission/config/ # Config de Transmission(idem)
├── prowlarr/config/     # Config de Prowlarr    (idem)
├── plex/config/         # Config de Plex        (idem)
├── bazarr/config/       # Config de Bazarr      (idem)
└── media/               # ⭐ Directorio unificado (optimizado para hardlinks)
    ├── downloads/       # Descargas de Transmission
    │   ├── complete/    # Descargas completadas
    │   │   └── tv-sonarr/  # Categoría para Sonarr
    │   └── incomplete/  # Descargas en progreso
    ├── tv/              # Biblioteca de series (hardlinks)
    ├── movies/          # Biblioteca de películas (hardlinks)
    └── music/           # Biblioteca de música (hardlinks)
```

> ℹ️ Los directorios `*/config/` y `media/` **no están en el repositorio** (ver `.gitignore`). Docker los crea automáticamente la primera vez que levantas el stack.

## 🔗 Optimización de Hardlinks

**⚡ Sin Duplicación de Archivos**: Esta configuración utiliza hardlinks para evitar duplicar archivos entre `downloads/` y las bibliotecas `tv/`/`movies/`, ahorrando espacio en disco significativo.

### Cómo Funciona:
1. **Transmission** descarga archivos a `/media/downloads/complete/tv-sonarr/`
2. **Sonarr** procesa los archivos completados usando hardlinks
3. **Resultado**: Archivo físico único con múltiples referencias (sin duplicación)

### Verificar Hardlinks:
```bash
# Comparar inodos (deben ser iguales)
ls -li media/downloads/complete/tv-sonarr/serie/archivo.mkv
ls -li media/tv/serie/Season*/archivo.mkv

# Verificar espacio real usado
du -sh media/
```

## 🚀 Inicio Rápido

### 1. Clonar el repositorio
```bash
git clone <URL-DEL-REPOSITORIO> media-stack
cd media-stack
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env y ajusta PUID/PGID (usa `id -u` y `id -g`) y TZ a tu zona horaria
```

### 3. Iniciar el stack completo
```bash
docker compose up -d
```
La primera vez Docker descargará las imágenes y creará los directorios `*/config/` y `media/`. Luego abre cada servicio en su puerto (ver tabla de servicios) para configurarlo.

### 4. Detener el stack
```bash
docker compose down
```

### 5. Ver logs
```bash
docker compose logs -f          # todos los servicios
docker compose logs -f sonarr   # uno específico
```

### 6. Reiniciar un servicio específico
```bash
docker compose restart sonarr
# o radarr, lidarr, transmission, prowlarr, plex, bazarr
```

### 7. Actualizar el stack a la última versión
```bash
docker compose pull        # descarga las imágenes :latest más recientes
docker compose up -d       # recrea los contenedores
docker image prune -f      # libera las imágenes antiguas
```

## ⚙️ Configuración Inicial

> 🌐 **Nota sobre las URLs**: `http://localhost:<puerto>` funciona si abres el navegador **en la misma máquina** donde corre Docker. Desde otro equipo de la red, reemplaza `localhost` por la **IP del host** (ej. `http://192.168.1.50:8989`).
>
> 🔗 **Comunicación entre servicios**: cuando un servicio se conecta a otro (Prowlarr→Sonarr, Bazarr→Radarr, etc.) usa el **nombre del contenedor** como host (`sonarr`, `radarr`, `transmission`…), **no** `localhost`. Todos comparten la red por defecto de Docker Compose y se resuelven por nombre.

### 1. Prowlarr (http://localhost:9696)

**Configurar Indexers:**
1. Settings → Indexers → Add Indexer
2. Agrega indexers públicos como:
   - The Pirate Bay
   - 1337x
   - RARBG
   - YTS (para películas)

**Conectar Sonarr y Radarr:**
1. Settings → Apps → Add Application
2. Para Sonarr:
   - Name: `Sonarr`
   - Prowlarr Server: `http://localhost:9696`
   - Sonarr Server: `http://sonarr:8989`
   - API Key: Copiar desde Sonarr (Settings → General → API Key)
3. Para Radarr:
   - Name: `Radarr`
   - Prowlarr Server: `http://localhost:9696`
   - Radarr Server: `http://radarr:7878`
   - API Key: Copiar desde Radarr (Settings → General → API Key)

### 2. Transmission (http://localhost:9091)

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `admin`

**Configuración recomendada:**
1. Edit Preferences → Network
   - Cambiar puerto de escucha si es necesario (por defecto: 51413)
2. Security
   - Cambiar usuario y contraseña por seguridad

### 3. Sonarr (http://localhost:8989)

**Configurar Root Folder:**
1. Settings → Media Management → Root Folders → Add
   - Path: `/media/tv`

**Configurar Download Client:**
1. Settings → Download Clients → Add → Transmission
   - Name: `Transmission`
   - Host: `transmission`
   - Port: `9091`
   - Username: `admin`
   - Password: `admin`
   - Category: `tv-sonarr`

**Configurar Media Management (para hardlinks):**
1. Settings → Media Management
   - ✅ Use Hardlinks instead of Copy: `Yes`
   - ✅ Import Extra Files: `Yes` (opcional)
   - ✅ Delete empty folders: `Yes`

**Los indexers se sincronizan automáticamente desde Prowlarr**

### 4. Radarr (http://localhost:7878)

**Configurar Root Folder:**
1. Settings → Media Management → Root Folders → Add
   - Path: `/media/movies`

**Configurar Download Client:**
1. Settings → Download Clients → Add → Transmission
   - Name: `Transmission`
   - Host: `transmission`
   - Port: `9091`
   - Username: `admin`
   - Password: `admin`
   - Category: `radarr`

**Configurar Media Management (para hardlinks):**
1. Settings → Media Management
   - ✅ Use Hardlinks instead of Copy: `Yes`
   - ✅ Import Extra Files: `Yes` (opcional)
   - ✅ Delete empty folders: `Yes`

**Los indexers se sincronizan automáticamente desde Prowlarr**

### 5. Lidarr (http://localhost:8686)

**Configurar Root Folder:**
1. Settings → Media Management → Root Folders → Add
   - Path: `/media/music`

**Configurar Download Client:**
1. Settings → Download Clients → Add → Transmission
   - Name: `Transmission`
   - Host: `transmission`
   - Port: `9091`
   - Username: `admin`
   - Password: `admin`
   - Category: `lidarr`

**Configurar Media Management (para hardlinks):**
1. Settings → Media Management
   - ✅ Use Hardlinks instead of Copy: `Yes`
   - ✅ Delete empty folders: `Yes`

**Los indexers se sincronizan automáticamente desde Prowlarr**

### 6. Plex (http://localhost:32400/web)

**Configuración inicial:**
1. Crear cuenta de Plex (gratis) o iniciar sesión
2. Nombrar tu servidor
3. Agregar bibliotecas:
   - **TV Shows**:
     - Tipo: TV Shows
     - Ruta: `/media/tv`
   - **Movies**:
     - Tipo: Movies
     - Ruta: `/media/movies`
   - **Music**:
     - Tipo: Music
     - Ruta: `/media/music`
4. Plex escaneará automáticamente el contenido

### 7. Bazarr (http://localhost:6767)

**Configurar Sonarr:**
1. Settings → Sonarr
2. Enable Sonarr: ✅
3. Configurar:
   - Address: `sonarr`
   - Port: `8989`
   - API Key: Copiar desde Sonarr (Settings → General → API Key)
4. Test y Save

**Configurar Radarr:**
1. Settings → Radarr
2. Enable Radarr: ✅
3. Configurar:
   - Address: `radarr`
   - Port: `7878`
   - API Key: Copiar desde Radarr (Settings → General → API Key)
4. Test y Save

**Configurar Idiomas:**
1. Settings → Languages
2. Languages Filter: Selecciona los idiomas deseados
   - Español (Spanish)
   - Inglés (English)
   - Otros según necesites
3. Default Settings: Configura prioridades de idiomas

**Configurar Proveedores de Subtítulos:**
1. Settings → Providers
2. Agregar proveedores recomendados:
   - **OpenSubtitles**: Requiere cuenta gratuita (excelente base de datos)
   - **Subdivx**: Excelente para español latino
   - **Subscene**: Muchos idiomas disponibles
   - **Podnapisi**: No requiere registro
3. Guardar configuración

**Activar descarga automática:**
1. Settings → Sonarr → Download Only Monitored: ✅
2. Settings → Radarr → Download Only Monitored: ✅
3. Settings → Subtitles → Single Language: Desactivar si quieres múltiples idiomas

## 📥 Cómo Descargar Contenido

### Descargar Series (Sonarr)

1. Ir a http://localhost:8989
2. Click en **"Add Series"**
3. Buscar la serie deseada
4. Configurar:
   - Root Folder: `/media/tv`
   - Quality Profile: `HD-1080p` (recomendado)
   - Monitor: Episodios a descargar
5. Click **"Add Series"**
6. Sonarr buscará y descargará automáticamente

### Descargar Películas (Radarr)

1. Ir a http://localhost:7878
2. Click en **"Add Movie"**
3. Buscar la película
4. Configurar:
   - Root Folder: `/media/movies`
   - Quality Profile: `HD-1080p` (recomendado)
5. Click **"Add Movie"**
6. Radarr buscará y descargará automáticamente

## 🎬 Flujo Completo

```
Usuario agrega contenido
        ↓
Sonarr/Radarr buscan en indexers (vía Prowlarr)
        ↓
Encuentran torrent y lo envían a Transmission
        ↓
Transmission descarga el archivo a /media/downloads/complete
        ↓
Sonarr/Radarr crean hardlinks en /media/tv o /media/movies
        ↓
Bazarr detecta el nuevo archivo y descarga subtítulos
        ↓
Plex detecta el nuevo contenido y subtítulos
        ↓
¡Listo para ver con subtítulos!
```

## 🔧 Perfiles de Calidad Recomendados

### HD-1080p (Recomendado)
- ✅ Excelente calidad
- ✅ Tamaño razonable (3-15 GB por película)
- ✅ Compatible con cualquier TV moderna

### Ultra HD (4K)
- ✅ Máxima calidad visual
- ❌ Archivos muy pesados (25-80 GB por película)
- ❌ Requiere TV 4K

### HD-720p
- ✅ Archivos pequeños (1-4 GB por película)
- ⚠️ Calidad inferior a 1080p

## 🛠️ Comandos Útiles

### Ver estado de contenedores
```bash
docker ps
```

### Ver logs de un servicio específico
```bash
docker logs -f sonarr
docker logs -f radarr
docker logs -f transmission
docker logs -f prowlarr
docker logs -f plex
docker logs -f bazarr
```

### Actualizar imágenes
```bash
docker compose pull
docker compose up -d
```

### Reiniciar todo el stack
```bash
docker compose restart
```

### Eliminar todo (cuidado: borra contenedores, no datos)
```bash
docker compose down
```

## 📊 Monitoreo

- **Transmission**: Ver progreso de descargas en http://localhost:9091
- **Sonarr/Radarr**: Activity → Queue para ver estado de descargas
- **Bazarr**: History muestra subtítulos descargados
- **Plex**: Dashboard muestra actividad de reproducción

## 🔐 Seguridad

### Recomendaciones:
1. **Cambiar credenciales de Transmission** (por defecto admin/admin)
2. **Configurar autenticación** en Sonarr/Radarr (Settings → General)
3. **No exponer puertos** a internet sin VPN/autenticación
4. **Usar VPN** para descargas torrent (opcional pero recomendado)

## 📸 Config snapshots (versionado sin secretos)

El repositorio versiona **copias sanitizadas** de la configuración de cada app en `configs/`, generadas por script: cada campo sensible (API keys, tokens, passwords, credenciales de providers) se reemplaza por un placeholder nombrado tipo `{{SONARR_API_KEY}}`. Las configs vivas de `*/config/` siguen ignoradas por git.

### Regenerar los snapshots (tras cambiar settings en alguna app)

```bash
./scripts/config-backup.sh   # sanitiza configs vivas → configs/ y verifica que no hay secretos
git diff configs/            # revisar SIEMPRE el diff antes de commitear
git add configs/ && git commit -m "chore(configs): snapshot"
```

El script **falla** si el resultado contiene algo que parezca un secreto. La redacción combina una lista explícita de campos por servicio y una regla genérica por nombre de clave (`*password*`, `*token*`, `*api_key*`…) que cubre campos nuevos que las apps añadan — ambas en `scripts/sanitize.py`.

### Guardia anti-secretos (pre-commit)

Tras clonar, activa el hook (la config de git no viaja con el clone):

```bash
git config core.hooksPath scripts/githooks
```

Bloquea cualquier commit cuyo contenido staged contenga un secreto real de las configs vivas o algo que lo parezca (32 hex, JWT, PEM, `password=...`). También puede ejecutarse a mano: `./scripts/config-check.sh`.

### Secretos de Recyclarr

`recyclarr/config/recyclarr.yml` se versiona directamente (Recyclarr no reescribe su config) y referencia las API keys con `!secret`. Al clonar:

```bash
cp recyclarr/config/secrets.yml.example recyclarr/config/secrets.yml
# rellenar con las API keys reales (secrets.yml está en .gitignore)
```

> ⚠️ Los snapshots son **documentación/backup unidireccional**, no un restore automático: el estado real (indexers, perfiles, series) vive en las bases de datos SQLite de cada app. Para disaster recovery usa el backup nativo de cada app (`Settings → General → Backups`).

## 🌐 Acceso Remoto con Plex

Para acceder a tu contenido desde fuera de casa:
1. Cuenta Plex maneja el acceso remoto automáticamente
2. Settings → Network → Enable Remote Access
3. Plex se encarga del port forwarding y túneles

## 📝 Notas

- **Zona horaria**: Configurada como `Europe/Madrid` (cambiar `TZ` en el archivo `.env` si es necesario)
- **PUID/PGID**: Configurados como 1000 (usuario estándar de Linux), definidos en `.env`
- **Respaldo y secretos**: El repositorio versiona la infraestructura (`docker-compose.yml`, `README.md`, `.env.example`) y **snapshots sanitizados** de las configs en `configs/` (ver sección "Config snapshots"). Los directorios `*/config/` vivos están en `.gitignore` porque contienen secretos (API keys, contraseñas, token de Plex) y bases de datos. Para respaldar la configuración real usa el backup nativo de cada app (`Settings → General → Backups`) o copia los `config/` por fuera de git.
- **Network mode**: Plex usa `host` para mejor rendimiento y descubrimiento de dispositivos
- **Reinicio automático**: Todos los servicios se reinician automáticamente si fallan

## 🆘 Solución de Problemas

## 💾 Gestión Eficiente de Espacio

### ⚡ Problema Resuelto: Duplicación de Archivos

Esta configuración **elimina la duplicación** de archivos que ocurría en versiones anteriores:

**❌ Antes (Problemático):**
```
downloads/    48 GB
tv/          48 GB  ← DUPLICADO
movies/      15 GB  ← DUPLICADO
Total:       111 GB (con ~63 GB duplicados)
```

**✅ Ahora (Optimizado):**
```
media/
├── downloads/  48 GB (archivos originales)
├── tv/         0 GB  (hardlinks, sin espacio adicional)
└── movies/     0 GB  (hardlinks, sin espacio adicional)
Total:         48 GB (sin duplicación)
```

### 🔍 Verificar que los Hardlinks Funcionan:

```bash
# 1. Verificar que los archivos comparten el mismo inode
ls -li media/downloads/complete/tv-sonarr/serie/archivo.mkv
ls -li media/tv/serie/Season*/archivo.mkv
# Los números al inicio (inodos) deben ser IGUALES

# 2. Verificar espacio real usado
du -sh media/
# Debe mostrar aproximadamente el tamaño de una copia, no el doble

# 3. Verificar link count
stat media/tv/serie/Season*/archivo.mkv | grep Links
# Debe mostrar "Links: 2" o más
```

### 🚨 Si los Hardlinks No Funcionan:

1. **Verificar configuración de Sonarr/Radarr:**
   - Settings → Media Management
   - ✅ "Use Hardlinks instead of Copy" debe estar habilitado

2. **Verificar que todos los servicios usan `/media`:**
   ```bash
   docker exec sonarr ls -la /media/
   docker exec radarr ls -la /media/
   docker exec transmission ls -la /media/
   ```

3. **Re-procesar archivos existentes:**
   ```bash
   # Mover archivos duplicados y forzar re-importación
   rm -rf media/tv/* media/movies/*
   # Luego usar "Manual Import" en Sonarr/Radarr
   ```

## 🔧 Troubleshooting

### Transmission no descarga
- Verificar que el puerto 51413 esté abierto
- Revisar logs: `docker logs -f transmission`

### Sonarr/Radarr no encuentran torrents
- Verificar que Prowlarr tenga indexers configurados
- Verificar conexión entre Prowlarr y Sonarr/Radarr (Settings → Apps)

### Plex no detecta archivos nuevos
- Forzar escaneo: Biblioteca → ... → Scan Library Files
- Verificar permisos de archivos en /tv y /movies

### Bazarr no descarga subtítulos
- Verificar que los proveedores estén configurados correctamente
- Verificar conexión con Sonarr/Radarr (Settings → General)
- Revisar logs: `docker logs -f bazarr`
- Algunos proveedores requieren cuenta (ej: OpenSubtitles)

### No puedo acceder a un servicio
- Verificar que el contenedor esté corriendo: `docker ps`
- Revisar logs del servicio específico

## 🌍 Configuración de Subtítulos Múltiples

### Para descargar subtítulos en varios idiomas:

1. **En Bazarr** → Settings → Languages:
   - Languages Filter: Agrega todos los idiomas que quieras
   - Ejemplo: Español, English, Português
   
2. **Configurar prioridad**:
   - Series/Movies → Editar serie/película
   - Languages Profile: Selecciona los idiomas
   - Orden de prioridad: Arrastra para ordenar

3. **Subtítulos forzados** (para idiomas extranjeros en películas):
   - Settings → Subtitles
   - Forced: ✅ Enable

### Proveedores recomendados por idioma:

- **Español**: Subdivx, OpenSubtitles
- **Inglés**: OpenSubtitles, Subscene, Podnapisi
- **Portugués**: OpenSubtitles, LegendasTV (requiere cuenta)
- **Múltiples**: OpenSubtitles (mejor opción universal)

## 📚 Enlaces Útiles

- [Sonarr Wiki](https://wiki.servarr.com/sonarr)
- [Radarr Wiki](https://wiki.servarr.com/radarr)
- [Prowlarr Wiki](https://wiki.servarr.com/prowlarr)
- [Bazarr Wiki](https://wiki.bazarr.media/)
- [Plex Support](https://support.plex.tv/)
- [LinuxServer.io Documentation](https://docs.linuxserver.io/)

---

**¡Disfruta de tu media server automatizado! 🎉**
