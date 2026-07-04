#!/usr/bin/env bash
# Guardia anti-secretos. Falla (exit != 0) si:
#   1. Algún valor secreto REAL (extraído en memoria de las configs vivas y del
#      .env vía sanitize.py --list-secrets) aparece literal en configs/ o en el
#      contenido staged para commit.
#   2. Alguna heurística de secreto (32 hex, JWT eyJ..., clave PEM, password=...)
#      matchea en configs/ o en las líneas añadidas del staged (excluyendo
#      scripts/ y líneas con placeholders {{...}}).
# Nunca imprime el valor del secreto, solo dónde está.
# Usable a mano, desde config-backup.sh y como hook pre-commit.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

# ── 1. Valores reales, grep literal ──────────────────────────────────────────
staged_diff="$(git diff --cached -U0 2>/dev/null || true)"
while IFS= read -r secret; do
  [ -z "$secret" ] && continue
  if [ -d configs ]; then
    if hits=$(grep -rlF -- "$secret" configs/ 2>/dev/null); then
      echo "ERROR: valor secreto real presente en: ${hits}" >&2
      fail=1
    fi
  fi
  if [ -n "$staged_diff" ] && printf '%s' "$staged_diff" | grep -qF -- "$secret"; then
    echo "ERROR: valor secreto real en el contenido staged (git diff --cached)" >&2
    fail=1
  fi
done < <(python3 scripts/sanitize.py --list-secrets)

# ── 2. Heurísticas ───────────────────────────────────────────────────────────
heur="([a-fA-F0-9]{32})|(eyJ[A-Za-z0-9_-]{20,})|(-----BEGIN )|((password|passwd|token|secret|api_?key)[\"']?[[:space:]]*[:=][[:space:]]*[\"']?[^\"'{[:space:]]{8,})"

if [ -d configs ]; then
  if hits=$(grep -rInE "$heur" configs/ | grep -v '{{' || true); [ -n "$hits" ]; then
    echo "ERROR: posible secreto (heurística) en configs/:" >&2
    printf '%s\n' "$hits" | cut -d: -f1,2 >&2
    fail=1
  fi
fi

staged_added="$(git diff --cached -U0 -- . ':(exclude)scripts/' 2>/dev/null | grep '^+' | grep -v '^+++' || true)"
if [ -n "$staged_added" ]; then
  if printf '%s\n' "$staged_added" | grep -v '{{' | grep -qE "$heur"; then
    # Solo posiciones, nunca el contenido de la línea (contiene el secreto)
    echo "ERROR: posible secreto (heurística) en el contenido staged, líneas añadidas nº:" >&2
    printf '%s\n' "$staged_added" | grep -v '{{' | grep -nE "$heur" | cut -d: -f1 | tr '\n' ' ' >&2
    echo >&2
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  echo "config-check: BLOQUEADO — revisa los errores de arriba." >&2
  exit 1
fi
echo "config-check: OK (sin secretos en configs/ ni en lo staged)." >&2
