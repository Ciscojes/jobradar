# JobRadar Production Readiness

Este checklist deja JobRadar listo para desplegar. Lo único que debe decidirse al final es la plataforma y los dominios.

## Variables obligatorias

Copia `.env.production.example` como `.env` en el entorno de producción y rellena:

- `APP_ENV=production`
- `SECRET_KEY`: valor aleatorio de 32+ caracteres.
- `POSTGRES_PASSWORD` o `DATABASE_URL` si usas una base gestionada.
- `BACKEND_CORS_ORIGINS`: URL pública del dashboard.
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

## Decisiones pendientes

- Plataforma: VPS, Render, Railway, Fly.io, AWS, GCP, Azure, etc.
- Dominios: API y dashboard.
- HTTPS/proxy: proveedor gestionado o reverse proxy.
- Scheduler: embebido en API para MVP, worker separado para producción más estricta.
- Backups de PostgreSQL.
