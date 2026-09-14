# Runbook operativo de JobRadar

## Señales de salud

- `GET /health/live`: confirma que el proceso HTTP está vivo.
- `GET /health`: comprueba la conexión a la base de datos.
- `GET /health/ready`: exige base disponible y heartbeat reciente del worker.
- `GET /scheduler/status` (autenticado): muestra heartbeat, ejecuciones y tamaño de colas.
- Cada respuesta incluye `X-Request-ID`; en producción los logs son JSON y contienen ese ID.
- `GET /metrics`: formato Prometheus; en producción debe activarse con `METRICS_ENABLED=true`,
  protegerse con `METRICS_TOKEN` y limitarse en el proxy a la red de monitorización.

Alertar cuando `/health/ready` responda `503`, el worker aparezca como `is_stale`, aumente
`notifications_failed` o una cola crezca durante varios intervalos consecutivos.

## Colas persistentes

El worker procesa tres colas: sincronizaciones manuales, búsquedas por alerta y
notificaciones. Los trabajos de alerta se deduplican mientras están pendientes o en curso y
usan reintentos con backoff. Reiniciar API o worker no pierde los trabajos.

Si un trabajo queda en `running` por una caída, su `available_at` permite recuperarlo después
del período de reclamación. Investiga `error_message` antes de reintentar trabajos `failed`.

## Backup y restauración

Crear un respaldo cifrado por el almacenamiento de la plataforma:

```bash
DATABASE_URL='postgresql://...' scripts/backup_postgres.sh
```

Probar mensualmente la restauración en una base vacía y aislada:

```bash
RESTORE_DATABASE_URL='postgresql://.../jobradar_restore_test' \
  scripts/restore_postgres.sh backups/jobradar-AAAAMMDD.dump --confirm
```

Nunca pruebes una restauración sobre producción. Conserva una política de retención acorde
con la plataforma y verifica que los archivos no sean públicos.

## Prueba de carga de staging

Ejecutar contra staging, nunca contra proveedores externos ni producción sin autorización:

```bash
python scripts/load_check.py --url https://api-staging.example.com/health \
  --requests 200 --concurrency 20 --max-p95-ms 1000
```

## Despliegue y rollback

1. Crear backup antes de migraciones destructivas.
2. Construir imágenes y ejecutar la suite de CI.
3. Ejecutar `alembic upgrade head` una sola vez.
4. Arrancar API, worker y frontend Next.js.
5. Esperar `/health/ready` y ejecutar `scripts/smoke_check.py`.
6. Si falla, conservar la base migrada cuando la migración sea compatible y volver a la
   imagen anterior. Un downgrade de esquema requiere revisión manual y backup confirmado.

## Incidentes externos

- Adzuna/InfoJobs: las llamadas tienen timeout y reintentos breves; los trabajos aplican
  backoff persistente. No aumentes reintentos durante una caída prolongada.
- Indeed: puede bloquear scraping. En producción el fallo se registra y no se generan ofertas
  simuladas.
- Telegram: revisar `notification_logs` y `notification_outbox`; rotar el token si pudo quedar
  expuesto.
