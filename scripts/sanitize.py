#!/usr/bin/env python3
"""Genera snapshots sanitizados de las configs vivas del stack en configs/.

Cada campo sensible se reemplaza por un placeholder nombrado ({{SONARR_API_KEY}})
derivado de la ruta de la clave. La redacción combina:
  1. Lista explícita de rutas por servicio (SERVICES[*]["redact"]).
  2. Regla genérica: toda clave hoja cuyo nombre parezca sensible se redacta
     aunque no esté en la lista (defensa frente a campos nuevos que las apps
     añadan en caliente).

Modos:
  sanitize.py                 escribe los snapshots en configs/
  sanitize.py --list-secrets  imprime a stdout los valores secretos reales
                              (para que config-check.sh los grepee; nunca a disco)
"""

import configparser
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Regla genérica: nombres de clave que se redactan siempre que tengan valor.
# Falsos positivos aceptables: mejor un placeholder de más que un secreto de menos.
# Excepciones puntuales → añadir la ruta completa a KEEP.
SENSITIVE_KEY_RE = re.compile(
    r"(api_?key|passwd|password|token|secret|cookie|user_?name|email|hashed"
    r"|webhook|vapid|client_?id|machine_?id|bot_?api|chat_?id|captcha|uuid"
    r"|identifier|_key$|^key$)",
    re.IGNORECASE,
)

# Rutas (con la sintaxis de "redact") que NUNCA se redactan aunque matcheen
# la regla genérica. Decisión siempre manual.
KEEP = set()

# Entre los valores que config-check.sh grepea literalmente solo van los
# secretos fuertes; usernames/emails se redactan en el snapshot pero no se
# grepean (p.ej. "macuartin" aparece legítimamente en la URL del repo).
STRONG_SECRET_KEY_RE = re.compile(
    r"(key|token|secret|password|passwd|vapid|captcha|hashed|cookie)", re.IGNORECASE
)

SERVICES = {
    "sonarr": {
        "src": "sonarr/config/config.xml",
        "dst": "configs/sonarr/config.xml",
        "format": "xml",
        "redact": ["ApiKey", "SslCertPassword"],
    },
    "radarr": {
        "src": "radarr/config/config.xml",
        "dst": "configs/radarr/config.xml",
        "format": "xml",
        "redact": ["ApiKey", "SslCertPassword"],
    },
    "lidarr": {
        "src": "lidarr/config/config.xml",
        "dst": "configs/lidarr/config.xml",
        "format": "xml",
        "redact": ["ApiKey", "SslCertPassword"],
    },
    "prowlarr": {
        "src": "prowlarr/config/config.xml",
        "dst": "configs/prowlarr/config.xml",
        "format": "xml",
        "redact": ["ApiKey", "SslCertPassword"],
    },
    "transmission": {
        "src": "transmission/config/settings.json",
        "dst": "configs/transmission/settings.json",
        "format": "json",
        "redact": ["rpc-password", "rpc-username"],
    },
    "bazarr": {
        "src": "bazarr/config/config/config.yaml",
        "dst": "configs/bazarr/config.yaml",
        "format": "yaml",
        "redact": [
            "auth.apikey",
            "auth.password",
            "general.flask_secret_key",
            "plex.token",
            "plex.server_url",
            "plex.encryption_key",
            "plex.email",
            "plex.username",
            "plex.user_id",
            "sonarr.apikey",
            "radarr.apikey",
        ],
    },
    "seerr": {
        "src": "seerr/config/settings.json",
        "dst": "configs/seerr/settings.json",
        "format": "json",
        "redact": [
            "clientId",
            "sessionSecret",
            "vapidPrivate",
            "vapidPublic",
            "main.apiKey",
            "plex.machineId",
            "jellyfin.apiKey",
            "jellyfin.serverId",
            # IDs de biblioteca: no son secretos, pero son 32-hex y disparan
            # la heurística anti-secretos; fuera del snapshot no aportan nada
            "jellyfin.libraries.*.id",
            "radarr.*.apiKey",
            "sonarr.*.apiKey",
        ],
    },
    # Jellyfin reparte su config en varios XML; los secretos (API keys, users)
    # viven en su base de datos, no en estos ficheros — la regla genérica queda
    # como respaldo por si un update introduce claves sensibles.
    "jellyfin": {
        "src": "jellyfin/config/system.xml",
        "dst": "configs/jellyfin/system.xml",
        "format": "xml",
        "redact": [],
    },
    "jellyfin-network": {
        "src": "jellyfin/config/network.xml",
        "dst": "configs/jellyfin/network.xml",
        "format": "xml",
        "redact": [],
    },
    "jellyfin-encoding": {
        "src": "jellyfin/config/encoding.xml",
        "dst": "configs/jellyfin/encoding.xml",
        "format": "xml",
        "redact": [],
    },
}


def is_empty(value):
    if value is None or value is False or value == 0:
        return True
    if isinstance(value, str):
        return value.strip().strip("\"'") == ""
    return False


def camel_to_snake(name):
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)


def placeholder(service, path):
    parts = [service] + [str(p) for p in path]
    slug = "_".join(re.sub(r"[^A-Za-z0-9]+", "_", camel_to_snake(p)) for p in parts)
    slug = re.sub(r"_+", "_", slug).strip("_").upper()
    return "{{%s}}" % slug


def path_matches(path, spec):
    """spec: "plex.token" o "radarr.*.apiKey" ('*' = cualquier índice de lista)."""
    parts = spec.split(".")
    if len(parts) != len(path):
        return False
    return all(s == "*" or str(p) == s for s, p in zip(parts, path))


def should_redact(path, key, redact_specs):
    if any(path_matches(path, spec) for spec in KEEP):
        return False
    if any(path_matches(path, spec) for spec in redact_specs):
        return True
    return bool(SENSITIVE_KEY_RE.search(str(key)))


class Collector:
    """Acumula los valores secretos redactados (solo en memoria)."""

    def __init__(self):
        self.values = []  # (path, value, key)

    def add(self, path, key, value):
        self.values.append((tuple(path), str(key), value))

    def strong_values(self):
        out = []
        for path, key, value in self.values:
            if not STRONG_SECRET_KEY_RE.search(key):
                continue
            v = str(value).strip().strip("\"'")
            if len(v) >= 6:
                out.append(v)
        return out


def sanitize_tree(node, service, redact_specs, collector, path=()):
    if isinstance(node, dict):
        return {
            k: sanitize_leaf_or_tree(k, v, service, redact_specs, collector, path + (k,))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [
            sanitize_tree(v, service, redact_specs, collector, path + (i,))
            for i, v in enumerate(node)
        ]
    return node


def sanitize_leaf_or_tree(key, value, service, redact_specs, collector, path):
    if isinstance(value, (dict, list)):
        return sanitize_tree(value, service, redact_specs, collector, path)
    if should_redact(path, key, redact_specs) and not is_empty(value):
        collector.add(path, key, value)
        return placeholder(service, path)
    return value


def sanitize_xml(text, service, redact_specs, collector):
    """XML plano de un nivel (config.xml de los *arr): reemplazo por tag."""
    for tag in redact_specs:
        pattern = re.compile(r"(<%s>)([^<]+)(</%s>)" % (tag, tag))

        def repl(m, tag=tag):
            collector.add((tag,), tag, m.group(2))
            return m.group(1) + placeholder(service, (tag,)) + m.group(3)

        text = pattern.sub(repl, text)
    return text


def sanitize_ini(text, service, redact_specs, collector):
    parser = configparser.RawConfigParser(strict=False)
    parser.optionxform = str
    parser.read_string(text)
    for section in parser.sections():
        for key, value in parser.items(section):
            if is_empty(value):
                continue
            if should_redact((section, key), key, redact_specs):
                collector.add((section, key), key, value)
                ph = placeholder(service, (section, key))
                if value.startswith('"') and value.endswith('"'):
                    ph = '"%s"' % ph
                parser.set(section, key, ph)
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue()


def sanitize_service(name, cfg, collector):
    src = ROOT / cfg["src"]
    text = src.read_text(encoding="utf-8")
    fmt = cfg["format"]
    if fmt == "xml":
        return sanitize_xml(text, name, cfg["redact"], collector)
    if fmt == "json":
        data = json.loads(text)
        clean = sanitize_tree(data, name, cfg["redact"], collector)
        return json.dumps(clean, indent=4, ensure_ascii=False) + "\n"
    if fmt == "yaml":
        data = yaml.safe_load(text)
        clean = sanitize_tree(data, name, cfg["redact"], collector)
        return yaml.safe_dump(
            clean, sort_keys=False, default_flow_style=False, allow_unicode=True
        )
    if fmt == "ini":
        return sanitize_ini(text, name, cfg["redact"], collector)
    raise ValueError("formato desconocido: %s" % fmt)


def env_secrets():
    """Valores sensibles del .env (para --list-secrets)."""
    out = []
    env = ROOT / ".env"
    if not env.exists():
        return out
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("\"'")
        if STRONG_SECRET_KEY_RE.search(key) and len(value) >= 6:
            out.append(value)
    return out


def atomic_write(dst, content):
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=".tmp-sanitize-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, dst)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv):
    list_secrets = "--list-secrets" in argv
    collector = Collector()
    missing = []
    for name, cfg in SERVICES.items():
        src = ROOT / cfg["src"]
        if not src.exists():
            missing.append(cfg["src"])
            continue
        content = sanitize_service(name, cfg, collector)
        if not list_secrets:
            atomic_write(ROOT / cfg["dst"], content)
            print("  %s -> %s" % (cfg["src"], cfg["dst"]), file=sys.stderr)
    if missing and not list_secrets:
        print("AVISO: fuentes no encontradas: %s" % ", ".join(missing), file=sys.stderr)
    if list_secrets:
        for value in sorted(set(collector.strong_values() + env_secrets())):
            print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
