# JobRadar Production Readiness

Este checklist deja JobRadar listo para desplegar. Lo único que debe decidirse al final es la plataforma y los dominios.

## Variables obligatorias

Copia `.env.production.example` como `.env` en el entorno de producción y rellena:

- `APP_ENV=production`
- `SECRET_KEY`: valor aleatorio de 32+ caracteres.
- `POSTGRES_PASSWORD`: contraseña del PostgreSQL incluido en Compose.
- `DATABASE_URL` (opcional): si se define, la API usa esa base gestionada en lugar de la URL interna.
- `BACKEND_CORS_ORIGINS`: URL pública del dashboard.
- `TRUSTED_HOSTS`: hostnames públicos permitidos para la API/dashboard.
- `TELEGRAM_BOT_TOKEN`: token privado del bot oficial.
- `TELEGRAM_BOT_USERNAME`: username público del bot, sin `@`.
- `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY`.
- `SMTP_*` si se activa email real.

En producción `AUTO_CREATE_TABLES=false`; el esquema se aplica con Alembic.

## Arranque con Docker Compose

```bash
cp .env.production.example .env
docker compose -f docker-compose.prod.yml up --build -d
```

El servicio `api` ejecuta:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

El servicio `worker` procesa búsquedas programadas, sincronizaciones manuales y el outbox
de notificaciones. `WORKER_POLL_INTERVAL_SECONDS` controla la frecuencia de las colas.

## Smoke test

Cuando API y dashboard estén levantados:

```bash
python scripts/smoke_check.py \
  --api-url http://localhost:8000 \
  --dashboard-url http://localhost:8501
```

En plataforma real, sustituye esas URLs por las URLs públicas o internas disponibles.

El smoke test valida:

- `/health`
- dashboard HTTP
- registro/login de usuario smoke
- `/auth/me`
- `/notificaciones/canales`
- `/scheduler/status`

## Telegram oficial

El usuario final no ve el token.

1. El servidor define `TELEGRAM_BOT_TOKEN`.
2. El dashboard muestra `TELEGRAM_BOT_USERNAME`.
3. El usuario abre el bot desde `Avisos`.
4. Pulsa `Start` en Telegram.
5. Vuelve a JobRadar y pulsa `Detectar mi chat ID`.
6. Agrega el aviso y prueba el canal.

Antes de producción, rota cualquier token que se haya usado durante pruebas.

## Seguridad final antes de exponerlo

- Rotar `TELEGRAM_BOT_TOKEN`, `SECRET_KEY`, credenciales de Adzuna y SMTP si fueron compartidas durante pruebas.
- Usar `APP_ENV=production`, `AUTO_CREATE_TABLES=false` y migraciones Alembic.
- Configurar `BACKEND_CORS_ORIGINS` con el dominio real del dashboard; no usar `*`.
- Configurar `TRUSTED_HOSTS` con los hostnames reales; no usar `*`.
- Mantener `.env` fuera de git y cargar secretos desde la plataforma.
- Activar HTTPS obligatorio en API y dashboard.
- Mantener activas las cabeceras de seguridad de la API (`nosniff`, `DENY`, `no-referrer`, HSTS en producción).
- Usar una base PostgreSQL con contraseña fuerte y backups.
- Mantener `DOCS_ENABLED=false` si Swagger no debe ser público.
- Ejecutar `scripts/smoke_check.py` después de cada despliegue.
- Revisar logs de `failed` en notificaciones y errores 401/429.
- Verificar `/health/ready` y conectar los request IDs/logs JSON al agregador elegido.
- Programar `scripts/backup_postgres.sh` y probar `scripts/restore_postgres.sh` en una base aislada.
- Varias réplicas de API comparten límites y colas mediante PostgreSQL. Los jobs usan bloqueo y deduplicación.

## Decisiones pendientes

- Plataforma: VPS, Render, Railway, Fly.io, AWS, GCP, Azure, etc.
- Dominios: API y dashboard.
- HTTPS/proxy: proveedor gestionado o reverse proxy.
- Conectar las métricas y el heartbeat expuestos en `/scheduler/status` al monitor elegido.
- Proveedor y retención definitiva para backups de PostgreSQL.

Procedimientos detallados: [runbook operativo](operations-runbook.md).
