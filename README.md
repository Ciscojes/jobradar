<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00FF41,100:0d1117&height=220&section=header&text=JobRadar&fontSize=70&fontColor=ffffff&fontAlignY=35&desc=SaaS%20de%20alertas%20de%20empleo%20multiusuario&descAlignY=55&descColor=ffffff&animation=fadeIn" width="100%"/>
</div>

<div align="center">

### _Plataforma SaaS que centraliza ofertas de empleo, las cruza con tu perfil y te avisa antes que a nadie_

<br/>

![Views](https://komarev.com/ghpvc/?username=jobradar-project&color=00FF41&style=for-the-badge&label=REPO+VIEWS)
[![Status](https://img.shields.io/badge/Status-En_producción-00FF41?style=for-the-badge)](/)
[![Made in Madrid](https://img.shields.io/badge/Made_in-Madrid_🇪🇸-00FF41?style=for-the-badge)](/)

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=python&logoColor=white)](https://sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-24_passing-00FF41?style=for-the-badge&logo=pytest&logoColor=white)](/)
[![License](https://img.shields.io/badge/License-MIT-00FF41?style=for-the-badge)](LICENSE)

<br/>

**[🚀 Instalación](#-instalación-rápida)** · **[📡 API](#-api-endpoints)** · **[🛠️ Stack](#️-stack-tecnológico)** · **[👨‍💻 Equipo](#-equipo)**

</div>

<br/>

---

## 🧠 ¿Qué es JobRadar?

**JobRadar** es una plataforma SaaS multiusuario que conecta con la **API de Adzuna**, guarda las ofertas en una base de datos propia, las cruza contra el perfil profesional de cada usuario y le notifica en tiempo real por **Telegram** o **email** en cuanto aparece algo que encaja con lo que busca.

No es un scraper frágil que se rompe con cada cambio de HTML: usa una API pública oficial, con autenticación JWT por usuario, base de datos relacional y arquitectura pensada para escalar a producción con Docker.

> 💡 _El objetivo no es que busques trabajo tú — es que el trabajo adecuado te encuentre a ti._

<br/>

<div align="center">

| 🔐 Auth JWT | 🧑‍🤝‍🧑 Multiusuario | 🗃️ Migraciones Alembic | 🐳 Docker Compose | 🧪 24 Tests |
|:---:|:---:|:---:|:---:|:---:|
| Sesiones seguras por usuario | Escalable a N clientes | Esquema versionado, sin scripts sueltos | Listo para producción | Auth · Alertas · Scheduler |

</div>

<br/>

---

## 🎯 ¿Qué demuestra este proyecto?

Este no es un script de scraping suelto — es una **aplicación SaaS completa de principio a fin**, pensada para simular un producto real en producción:

- **Arquitectura multiusuario real**, con autenticación JWT, permisos por usuario y aislamiento de datos entre cuentas.
- **Persistencia gestionada correctamente**: modelos relacionales con SQLAlchemy 2.0 y migraciones versionadas con Alembic (nada de `CREATE TABLE` sueltos).
- **Integración con una API externa real** (Adzuna), con manejo de errores y datos de fallback para desarrollo sin credenciales.
- **Automatización en segundo plano** con APScheduler: búsqueda periódica, matching por perfil y notificaciones sin intervención manual.
- **Notificaciones multicanal** (Telegram + email) desacopladas del núcleo de negocio.
- **Cobertura de tests** sobre autenticación, alertas, scheduler y notificaciones.
- **Contenedorización completa** con `docker-compose` (API + dashboard + base de datos).
- **Trabajo colaborativo real**: desarrollo en equipo con control de versiones, ramas y merges entre dos desarrolladores.

<br/>

---

## ✨ Funcionalidades

| Feature | Descripción |
|---|---|
| 🔐 **Autenticación JWT multiusuario** | Cada usuario tiene su propia sesión, sus propias alertas y sus propias ofertas |
| 🧑‍💼 **Perfil profesional** | Puesto deseado, ubicación, modalidad y nivel de experiencia — genera recomendaciones automáticamente |
| ⚡ **Recomendaciones instantáneas** | En cuanto te registras o creas una alerta, se busca y se muestra al momento, sin esperar al scheduler |
| 📡 **Integración con Adzuna** | Búsqueda de ofertas reales vía API oficial, con datos de prueba automáticos si no hay credenciales |
| 🔔 **Notificaciones multicanal** | Telegram y email por usuario, con mensaje de bienvenida automático al conectar un canal |
| ⏱️ **Scheduler automático** | Búsqueda periódica configurable con APScheduler, con historial de cada ejecución |
| 📋 **Seguimiento de ofertas** | Marca ofertas como `guardado`, `aplicado` o `descartado` |
| 🌐 **API REST documentada** | Swagger UI interactivo en `/docs` |
| 🖥️ **Dashboard completo** | Perfil, Ofertas, Alertas, Canales y Scraper — todo autenticado y en tiempo real |
| 🧪 **Tests automatizados** | Suite de 24 tests cubriendo auth, alertas, notificaciones y scheduler |
| 🐳 **Docker-ready** | `docker-compose` con FastAPI + Streamlit + PostgreSQL listos para desplegar |
| 🗃️ **Migraciones versionadas** | Esquema de base de datos gestionado con Alembic, sin scripts sueltos |

<br/>

---

## 🛠️ Stack tecnológico

```python
stack = {
    "backend":    ["FastAPI", "SQLAlchemy 2.0", "Pydantic", "APScheduler"],
    "database":   ["SQLite (dev)", "PostgreSQL (prod)", "Alembic (migraciones)"],
    "frontend":   ["Streamlit"],
    "auth":       ["JWT", "hashing propio (PBKDF2)"],
    "alertas":    ["Telegram Bot API", "SMTP / email"],
    "fuente":     ["Adzuna API"],
    "testing":    ["Pytest"],
    "devops":     ["Docker", "docker-compose"],
}
```

<br/>

---

## 📁 Estructura del proyecto

```
jobradar/
│
├── 📂 app/
│   ├── 🐍 main.py                    # Punto de entrada FastAPI
│   ├── 🐍 database.py                # Configuración SQLAlchemy
│   ├── 🐍 models.py                  # Modelos: usuarios, ofertas, alertas, canales, matches
│   ├── 🐍 schemas.py                 # Schemas Pydantic
│   │
│   ├── 📂 core/
│   │   └── 🐍 security.py            # Hashing de contraseñas, JWT
│   │
│   ├── 📂 scraper/
│   │   ├── 🐍 adzuna.py              # Integración con la API de Adzuna
│   │   └── 🐍 indeed.py              # Scraper complementario
│   │
│   ├── 📂 routers/
│   │   ├── 🐍 auth.py                # Registro, login, perfil
│   │   ├── 🐍 ofertas.py             # CRUD de ofertas
│   │   ├── 🐍 alertas.py             # Alertas + búsqueda instantánea
│   │   ├── 🐍 notificaciones.py      # Canales de notificación y logs
│   │   └── 🐍 scheduler.py           # Estado del scheduler
│   │
│   └── 📂 services/
│       ├── 🐍 scheduler.py           # Búsqueda automática + matching por usuario
│       ├── 🐍 notifications.py       # Envío multicanal
│       ├── 🐍 telegram.py            # Notificaciones por Telegram
│       └── 🐍 email.py               # Notificaciones por email
│
├── 📂 dashboard/
│   ├── 🐍 main.py                    # App Streamlit (Perfil, Ofertas, Alertas, Canales, Scraper)
│   └── 📂 components/
│
├── 📂 migrations/                    # Migraciones Alembic versionadas
│
├── 📂 tests/                         # 24 tests: API, scheduler, notificaciones, scraper
│
├── 🐳 docker-compose.yml
├── 📄 requirements.txt
├── 🔒 env.example
└── 📖 README.md
```

<br/>

---

## 🚀 Instalación rápida

### 1️⃣ Clona el repositorio

```bash
git clone https://github.com/Ciscojes/jobradar.git
cd jobradar
```

### 2️⃣ Entorno y dependencias

```bash
python -m venv venv
source venv/bin/activate       # Linux / macOS
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 3️⃣ Variables de entorno

```bash
cp env.example .env
```

```env
# Base de datos
DATABASE_URL=sqlite:///./jobradar.db

# Adzuna API → https://developer.adzuna.com
ADZUNA_APP_ID=tu_app_id
ADZUNA_APP_KEY=tu_app_key
ADZUNA_COUNTRY=es

# Telegram Bot → @BotFather
TELEGRAM_BOT_TOKEN=tu_token

# Email SMTP (opcional, se simula si no se configura)
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=

# Scheduler
SCRAPER_SCHEDULER_ENABLED=true
SCRAPER_INTERVAL_MINUTES=10
```

### 4️⃣ Migra la base de datos

```bash
alembic upgrade head
```

### 5️⃣ Arranca la API

```bash
uvicorn app.main:app --reload
```

### 6️⃣ Abre el dashboard

```bash
streamlit run dashboard/main.py
```

### 7️⃣ Docker Compose

Para desarrollo local con recarga automática, API, dashboard y PostgreSQL:

```bash
docker compose up --build
```

Para un despliegue tipo producción, sin recarga automática ni montajes del código:

```bash
POSTGRES_PASSWORD=change-me docker compose -f docker-compose.prod.yml up --build -d
```

En producción usa una contraseña real en `POSTGRES_PASSWORD` y conserva `.env` fuera de git.

<br/>

---

## 📡 API Endpoints

```
POST   /auth/register              → Registro (con perfil profesional opcional)
POST   /auth/login                 → Login, devuelve JWT
GET    /auth/me                    → Perfil del usuario autenticado
PATCH  /auth/me                    → Editar perfil (dispara recomendaciones al instante)

GET    /ofertas/                   → Lista de ofertas
PATCH  /ofertas/{id}/estado        → Actualiza estado (guardado / aplicado / descartado)

POST   /alertas/                   → Crea alerta (busca ofertas al momento)
GET    /alertas/                   → Lista de alertas
PATCH  /alertas/{id}/activar       → Reactiva alerta (vuelve a buscar al instante)
DELETE /alertas/{id}                → Elimina alerta

GET    /notificaciones/canales     → Canales de notificación del usuario
POST   /notificaciones/canales     → Añade canal (envía bienvenida automática)
POST   /notificaciones/canales/{id}/test → Prueba de envío
GET    /notificaciones/logs        → Historial de notificaciones

GET    /scheduler/status           → Estado del scheduler automático
POST   /scraper/sync               → Sincronización manual
GET    /scraper/runs               → Historial de ejecuciones del scraper
```

📚 Documentación interactiva disponible en: `http://localhost:8000/docs`

<br/>

---

## 🗺️ Roadmap

- [x] Arquitectura multiusuario con JWT
- [x] Modelos de datos y migraciones versionadas
- [x] Integración con Adzuna
- [x] Scheduler automático con matching por usuario
- [x] Notificaciones multicanal (Telegram + email)
- [x] Perfil profesional y recomendaciones instantáneas
- [x] Dashboard completo con Streamlit
- [x] Suite de tests automatizados
- [x] Dockerización con docker-compose
- [ ] Deploy en producción (VPS / Railway)
- [ ] Panel de estadísticas por usuario

<br/>

---

## 👨‍💻 Equipo

<div align="center">

| | Dev | Área |
|---|---|---|
| 🧑‍💻 | [**Oliver Lugo**](https://github.com/OLIVER26GOLDEN) | Backend · FastAPI · Base de datos · Integraciones · Scheduler |
| 🧑‍💻 | [**Jesús Granados**](https://github.com/Ciscojes) | Dashboard · Notificaciones · Tests |

</div>

<br/>

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.

<br/>

---

<div align="center">

**¿Te ha resultado útil? Dale una ⭐ al repo.**

<br/>

### 📬 ¿Hablamos?

Abierto a oportunidades como **Backend / Python Developer** en Madrid.

[![GitHub](https://img.shields.io/badge/GitHub-OLIVER26GOLDEN-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/OLIVER26GOLDEN)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Conectemos-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](#)

<br/>

_Built with 🖤 in Madrid_

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00FF41,100:0d1117&height=100&section=footer" width="100%"/>

</div>
