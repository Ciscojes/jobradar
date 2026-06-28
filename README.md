<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00FF41,100:0d1117&height=200&section=header&text=jobradar&fontSize=60&fontColor=00FF41&fontAlignY=38&desc=Radar%20de%20ofertas%20de%20empleo%20inteligente&descAlignY=58&descColor=ffffff&animation=fadeIn" width="100%"/>
</div>

<div align="center">

# 🎯 jobradar

### _Radar de ofertas de empleo — Infojobs API + filtros personalizados + alertas por Telegram_

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=python&logoColor=white)](https://sqlalchemy.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-00FF41?style=for-the-badge)](LICENSE)

<br/>

[![Status](https://img.shields.io/badge/🚧_Estado-En_Desarrollo-yellow?style=flat-square)](/)
[![API](https://img.shields.io/badge/📡_API-Infojobs_Oficial-blue?style=flat-square)](https://developer.infojobs.net)
[![Made with ❤️](https://img.shields.io/badge/Made_with-❤️_en_Madrid-red?style=flat-square)](/)

</div>

---

<br/>

## 🧠 ¿Qué es jobradar?

**jobradar** es una herramienta Python que conecta con la **API oficial de Infojobs**, centraliza las ofertas en una base de datos local y te avisa por **Telegram** en tiempo real cuando aparece una oferta que encaja con tu perfil.

Sin scraping. Sin bloqueos. Datos limpios, legales y actualizados.

> 💡 _Porque tu próximo trabajo no debería encontrarte a ti buscando manualmente._

<br/>

---

## ✨ Funcionalidades

| Feature | Descripción |
|--------|-------------|
| 📡 **Infojobs API Oficial** | Integración directa con la API pública de Infojobs, sin scraping |
| 🔍 **Filtros avanzados** | Por tecnología, ciudad, modalidad y salario |
| ⏱️ **Sync automático** | Nuevas ofertas cada X horas con APScheduler |
| 🔔 **Alertas Telegram** | Notificación instantánea cuando aparece una oferta a tu medida |
| 📋 **Seguimiento** | Marca ofertas como `aplicado`, `guardado` o `descartado` |
| 🌐 **API REST** | Endpoints documentados con Swagger UI |
| 🖥️ **Dashboard** | Interfaz visual con Streamlit para explorar y gestionar ofertas |

<br/>

---

## 🛠️ Stack tecnológico

```python
stack = {
    "backend":   ["FastAPI", "SQLAlchemy", "APScheduler", "Requests"],
    "database":  ["SQLite (dev)", "PostgreSQL (prod)"],
    "frontend":  ["Streamlit"],
    "alerts":    ["python-telegram-bot"],
    "api":       ["Infojobs API Oficial"],
    "devops":    ["Docker", "docker-compose"],
}
```

<br/>

---

## 📁 Estructura del proyecto

```
jobradar/
│
├── 📂 app/
│   ├── 🐍 main.py               # Punto de entrada FastAPI
│   ├── 🐍 database.py           # Configuración SQLAlchemy
│   ├── 🐍 models.py             # Modelos de base de datos
│   ├── 🐍 schemas.py            # Schemas Pydantic
│   │
│   ├── 📂 scraper/
│   │   ├── 🐍 infojobs.py       # API oficial de Infojobs
│   │   └── 🐍 indeed.py         # Scraper Indeed España
│   │
│   ├── 📂 routers/
│   │   ├── 🐍 ofertas.py        # CRUD de ofertas
│   │   └── 🐍 alertas.py        # Gestión de alertas
│   │
│   └── 📂 services/
│       ├── 🐍 scheduler.py      # Tareas periódicas
│       └── 🐍 telegram.py       # Notificaciones Telegram
│
├── 📂 dashboard/
│   ├── 🐍 app.py                # App Streamlit
│   └── 📂 components/
│
├── 📂 tests/
│   ├── 🐍 test_api.py
│   └── 🐍 test_scraper.py
│
├── 🐳 docker-compose.yml
├── 📄 requirements.txt
├── 🔒 .env.example
└── 📖 README.md
```

<br/>

---

## 🚀 Instalación rápida

### 1️⃣ Clona el repositorio

```bash
git clone https://github.com/OLIVER26GOLDEN/jobradar.git
cd jobradar
```

### 2️⃣ Entorno virtual + dependencias

```bash
python -m venv venv
source venv/bin/activate       # Linux / macOS
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 3️⃣ Variables de entorno

```bash
cp .env.example .env
```

```env
# Base de datos
DATABASE_URL=sqlite:///./jobradar.db

# Infojobs API → https://developer.infojobs.net
INFOJOBS_CLIENT_ID=tu_client_id
INFOJOBS_CLIENT_SECRET=tu_client_secret

# Telegram Bot → @BotFather
TELEGRAM_BOT_TOKEN=tu_token
TELEGRAM_CHAT_ID=tu_chat_id

# Scheduler
SCRAPER_INTERVAL_HOURS=6
```

### 4️⃣ Arranca el servidor

```bash
uvicorn app.main:app --reload
```

### 5️⃣ Abre el dashboard

```bash
streamlit run dashboard/app.py
```

<br/>

---

## 📡 API Endpoints

```
GET    /ofertas              → Lista de ofertas con filtros
GET    /ofertas/{id}         → Detalle de una oferta
PATCH  /ofertas/{id}/estado  → Actualiza estado (aplicado / guardado / descartado)
POST   /alertas              → Crea una alerta personalizada
GET    /alertas              → Lista de alertas activas
DELETE /alertas/{id}         → Elimina una alerta
POST   /scraper/sync         → Sincronización manual con Infojobs
```

📚 Documentación interactiva disponible en: `http://localhost:8000/docs`

<br/>

---

## 🗺️ Roadmap

- [x] Diseño de arquitectura
- [x] Estructura del proyecto
- [ ] Integración Infojobs API
- [ ] Modelos SQLAlchemy
- [ ] API REST con FastAPI
- [ ] Alertas por Telegram
- [ ] Scheduler automático
- [ ] Dashboard Streamlit
- [ ] Tests unitarios
- [ ] Dockerización
- [ ] Deploy en VPS / Railway

<br/>

---

## 👨‍💻 Equipo

<div align="center">

| | Dev | Área |
|--|-----|------|
| 🧑‍💻 | [**Oliver Lugo**](https://github.com/OLIVER26GOLDEN) | Backend · FastAPI · Base de datos · Servicios |
| 🧑‍💻 | [**Jesús Granados**](https://github.com/Ciscojes) | Dashboard · Filtros · Tests |

</div>

<br/>

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.

<br/>

---

<div align="center">

**¿Te ha resultado útil? Dale una ⭐ al repo — significa mucho.**

<br/>

_Built with 🖤 in Madrid_

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00FF41,100:0d1117&height=100&section=footer" width="100%"/>

</div>
