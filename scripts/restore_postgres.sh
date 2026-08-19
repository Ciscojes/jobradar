#!/usr/bin/env bash
set -euo pipefail

: "${RESTORE_DATABASE_URL:?Define RESTORE_DATABASE_URL con la base de destino}"

backup_path="${1:-}"
confirmation="${2:-}"
if [[ -z "$backup_path" || ! -f "$backup_path" ]]; then
  echo "Uso: RESTORE_DATABASE_URL=... $0 <backup.dump> --confirm" >&2
  exit 2
fi
if [[ "$confirmation" != "--confirm" ]]; then
  echo "La restauración reemplaza objetos existentes. Repite con --confirm." >&2
  exit 2
fi

pg_restore \
  --dbname="$RESTORE_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  "$backup_path"
echo "Restauración completada desde: $backup_path"
