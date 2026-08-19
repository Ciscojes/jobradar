#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Define DATABASE_URL con la base que quieres respaldar}"

backup_path="${1:-backups/jobradar-$(date -u +%Y%m%dT%H%M%SZ).dump}"
mkdir -p "$(dirname "$backup_path")"

pg_dump \
  --dbname="$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --file="$backup_path"
chmod 600 "$backup_path"
echo "Backup creado: $backup_path"
