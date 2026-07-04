#!/usr/bin/env bash
# Genera snapshots SANITIZADOS de las configs vivas en configs/ y verifica que
# no contienen secretos. Ejecución manual tras cambiar settings en alguna app:
#   ./scripts/config-backup.sh
#   git diff configs/        # revisar SIEMPRE antes de commitear
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Generando snapshots sanitizados..." >&2
python3 scripts/sanitize.py
scripts/config-check.sh
echo "OK — revisa 'git diff configs/' y commitea." >&2
