# 🚀 JobRadar

Plataforma SaaS para monitorizar ofertas de empleo utilizando FastAPI, PostgreSQL, Streamlit y Docker.

JobRadar permite a cada usuario crear alertas personalizadas, autenticar su sesion con JWT, consultar un dashboard privado y ejecutar busquedas automaticas de ofertas mediante un scheduler preparado para integrarse con InfoJobs.

**Stack principal:** Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy · Streamlit · APScheduler · Docker Compose

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## Objetivo

El objetivo de JobRadar es centralizar alertas de empleo personalizadas por usuario y automatizar la deteccion de ofertas relevantes desde fuentes externas. El proyecto esta construido como una base SaaS extensible, preparada para evolucionar hacia integraciones reales con InfoJobs, Telegram, email y despliegue en produccion.

En esta fase, el foco es tener una base estable y demostrable:

- API protegida con JWT.
- Base de datos preparada para multiples usuarios.
- CRUD completo de alertas.
- Dashboard que consume la API por HTTP.
- Scheduler automatico con APScheduler.
- Preparacion para conectar InfoJobs sin hardcodear credenciales.

## ✨ Características

- [x] Docker Compose
- [x] PostgreSQL
- [x] FastAPI
- [x] JWT
- [x] Dashboard autenticado
- [x] CRUD de alertas
- [x] Scheduler automático
- [x] Integración preparada para InfoJobs
- [x] Tests automatizados
- [ ] Telegram
- [ ] Email
- [ ] OAuth InfoJobs
- [ ] Deploy

## Arquitectura

```text
Usuario
  ↓
Dashboard Streamlit
  ↓
FastAPI
  ├── Auth
  ├── Alertas
  ├── Scheduler
  └── Scraper
  ↓
PostgreSQL
```

Componentes principales:

- `dashboard/app.py`: interfaz web autenticada.
- `app/main.py`: entrada principal de FastAPI.
- `app/routers/`: endpoints REST.
- `app/models.py`: modelos SQLAlchemy.
- `app/schemas.py`: schemas Pydantic.
- `app/scraper/infojobs.py`: preparacion para la API de InfoJobs.
- `app/services/scheduler.py`: ejecucion automatica de busquedas.
- `migrations/`: migraciones Alembic.
- `tests/`: pruebas automatizadas.

## Tecnologias Utilizadas

- Python 3.12
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Alembic
- Streamlit
- APScheduler
- Requests
- Pytest
- Docker
- Docker Compose

## Estructura de Carpetas

```text
jobradar/
├── app/
│   ├── core/
│   │   └── security.py
│   ├── routers/
│   │   ├── alertas.py
│   │   ├── auth.py
│   │   ├── notificaciones.py
│   │   └── ofertas.py
│   ├── scraper/
│   │   ├── indeed.py
│   │   └── infojobs.py
│   ├── services/
│   │   ├── email.py
│   │   ├── notifications.py
│   │   ├── scheduler.py
│   │   └── telegram.py
│   ├── database.py
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── dashboard/
│   ├── components/
│   ├── app.py
│   └── main.py
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── test_api.py
│   ├── test_scraper.py
│   ├── test_scheduler.py
│   └── test_sync.py
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements-api.txt
├── requirements-dashboard.txt
├── requirements.txt
└── README.md
```

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/Ciscojes/jobradar.git
cd jobradar
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

En Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Para instalaciones separadas:

```bash
pip install -r requirements-api.txt
pip install -r requirements-dashboard.txt
```

### 4. Crear archivo de entorno

```bash
cp .env.example .env
```

## Variables de Entorno

Ejemplo basado en `.env.example`:

```env
# Opcion rapida para desarrollo:
DATABASE_URL=sqlite:///./jobradar.db

# Opcion SaaS local con Docker Compose:
# DATABASE_URL=postgresql://jobradar:jobradar@localhost:5432/jobradar

SECRET_KEY=cambia-este-valor-en-produccion
ACCESS_TOKEN_EXPIRE_MINUTES=60

# InfoJobs: opcional. Si faltan, se usan datos de prueba.
INFOJOBS_CLIENT_ID=
INFOJOBS_CLIENT_SECRET=
INFOJOBS_REDIRECT_URI=http://localhost:8000/auth/infojobs/callback

# Telegram: pendiente. Cada usuario podra configurar su canal.
TELEGRAM_BOT_TOKEN=

# Email SMTP: pendiente. Si faltan, el envio se simulara.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=

# Scheduler: activo por defecto en desarrollo.
SCRAPER_SCHEDULER_ENABLED=true
SCRAPER_INTERVAL_MINUTES=10
SCRAPER_DEFAULT_QUERY=python

# Dashboard
API_URL=http://localhost:8000
```

Notas:

- En Docker Compose, el dashboard debe usar `API_URL=http://api:8000`.
- Si `INFOJOBS_CLIENT_ID` o `INFOJOBS_CLIENT_SECRET` estan vacios, JobRadar usa datos mock.
- El scheduler se ejecuta cada 10 minutos por defecto en desarrollo.
- No se deben hardcodear credenciales reales en el repositorio.

## Uso con Docker Compose

Levantar todos los servicios:

```bash
docker compose up -d
```

Servicios disponibles:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

Ver estado:

```bash
docker compose ps
```

Ver logs:

```bash
docker compose logs -f api
docker compose logs -f dashboard
docker compose logs -f postgres
```

Detener servicios:

```bash
docker compose down
```

## Ejecutar la API

Sin Docker:

```bash
uvicorn app.main:app --reload
```

La API queda disponible en:

- `http://localhost:8000`
- `http://localhost:8000/docs`

## Ejecutar el Dashboard

Sin Docker:

```bash
API_URL=http://localhost:8000 streamlit run dashboard/app.py
```

El dashboard queda disponible en:

```text
http://localhost:8501
```

El dashboard no se conecta directamente a la base de datos. Todas las operaciones pasan por FastAPI usando HTTP y JWT.

## 📷 Capturas

### Dashboard

![Dashboard de JobRadar](docs/images/dashboard-home.jpeg)

Dashboard autenticado donde cada usuario puede crear y administrar sus alertas de empleo.

---

### API REST (Swagger)

![Swagger de JobRadar](docs/images/swagger.jpeg)

Documentación interactiva de FastAPI con autenticación JWT y todos los endpoints disponibles.

---

## Endpoints Principales

### Auth

| Metodo | Endpoint         | Descripcion                 |
| ------ | ---------------- | --------------------------- |
| `POST` | `/auth/register` | Crear usuario               |
| `POST` | `/auth/login`    | Obtener JWT                 |
| `GET`  | `/auth/me`       | Obtener usuario autenticado |

### Alertas

| Metodo   | Endpoint                          | Descripcion                |
| -------- | --------------------------------- | -------------------------- |
| `GET`    | `/alertas/`                       | Listar alertas del usuario |
| `POST`   | `/alertas/`                       | Crear alerta               |
| `GET`    | `/alertas/{alerta_id}`            | Ver detalle de alerta      |
| `PUT`    | `/alertas/{alerta_id}`            | Editar alerta              |
| `PATCH`  | `/alertas/{alerta_id}/activar`    | Activar alerta             |
| `PATCH`  | `/alertas/{alerta_id}/desactivar` | Desactivar alerta          |
| `DELETE` | `/alertas/{alerta_id}`            | Eliminar alerta            |

### Ofertas

| Metodo  | Endpoint                      | Descripcion           |
| ------- | ----------------------------- | --------------------- |
| `GET`   | `/ofertas/`                   | Listar ofertas        |
| `POST`  | `/ofertas/`                   | Crear oferta          |
| `GET`   | `/ofertas/{oferta_id}`        | Ver detalle de oferta |
| `PATCH` | `/ofertas/{oferta_id}/estado` | Actualizar estado     |

### Scraper

| Metodo | Endpoint        | Descripcion                  |
| ------ | --------------- | ---------------------------- |
| `POST` | `/scraper/sync` | Sincronizacion manual actual |

### Scheduler

| Metodo | Endpoint            | Descripcion                                                        |
| ------ | ------------------- | ------------------------------------------------------------------ |
| `GET`  | `/scheduler/status` | Estado del scheduler, ultima ejecucion, proxima ejecucion y conteo |

La documentacion interactiva completa esta en:

```text
http://localhost:8000/docs
```

## Estado Actual del Desarrollo

Implementado:

- Docker Compose funcional.
- API FastAPI funcional.
- PostgreSQL funcional.
- Autenticacion JWT.
- Modelos base SaaS.
- CRUD completo de alertas.
- Dashboard autenticado.
- Scheduler automatico con APScheduler.
- Registro de ejecuciones en `ScraperRun`.
- Preparacion de InfoJobs con variables de entorno y datos mock.
- Tests automatizados.

Pendiente:

- OAuth e integracion real con InfoJobs.
- Notificaciones por Telegram.
- Notificaciones por email.
- Flujo completo de ofertas por usuario.
- Deploy.
- Documentacion con capturas reales.

## Roadmap

### v1.0

- [x] Docker
- [x] PostgreSQL
- [x] FastAPI
- [x] Dashboard
- [x] Auth
- [x] CRUD Alertas
- [x] Scheduler
- [x] Preparado para InfoJobs

### v1.1

- [ ] OAuth InfoJobs

### v1.2

- [ ] Telegram
- [ ] Email

### v2.0

- [ ] Deploy

## 🧪 Calidad del proyecto

JobRadar esta preparado como proyecto de portfolio tecnico y base SaaS extensible:

- 20 tests automatizados.
- Docker Compose funcional.
- Scheduler funcionando con APScheduler.
- API protegida con JWT.
- Arquitectura preparada para escalar por routers, servicios, modelos y scrapers.
- Dashboard desacoplado de la base de datos: se comunica unicamente con FastAPI por HTTP.

## Tests

Ejecutar tests:

```bash
.venv/bin/python -m pytest --ignore-glob='*-JESUSPC*'
```

Tambien puede usarse:

```bash
pytest
```

Los tests actuales cubren:

- Inicio basico de la API.
- Auth: registro, login y usuario autenticado.
- Rutas protegidas.
- CRUD de ofertas existente.
- CRUD de alertas.
- Aislamiento de alertas por usuario.
- Scrapers con mocks.
- Scheduler automatico.
- Sincronizacion mock.

## Licencia

Distribuido bajo licencia MIT. Consulta el archivo `LICENSE` si esta disponible en el repositorio.

## Autor

**Jesús Granados y Oliver Lugo**

Estudiante de Desarrollo Full Stack

GitHub:

https://github.com/Ciscojes

Este proyecto evoluciono a partir de una base inicial y actualmente continua siendo desarrollado por Jesús Granados Y Oliver Lugo.
