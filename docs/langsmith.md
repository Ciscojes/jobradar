# LangSmith en JobRadar

JobRadar usa búsquedas y reglas deterministas, no un LLM. LangSmith observa
tiempos, jerarquía y excepciones de operaciones; no añade generación de texto.
La integración es opcional y está desactivada por defecto, incluso si existen
`LANGSMITH_TRACING=true` o `LANGCHAIN_TRACING_V2=true` en el entorno.

## Activación

Instala el SDK opcional en el mismo entorno de la API y del worker:

```sh
python -m pip install --require-hashes -r requirements-langsmith.lock
```

Configura únicamente en los procesos del servidor y reinícialos:

```dotenv
JOBRADAR_LANGSMITH_ENABLED=true
JOBRADAR_LANGSMITH_SAMPLE_RATE=0.1
LANGSMITH_API_KEY=<clave privada de LangSmith>
LANGSMITH_PROJECT=jobradar-production
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

`JOBRADAR_LANGSMITH_SAMPLE_RATE` admite valores entre 0 y 1. El muestreo se
decide para la raíz y se hereda por sus hijos. Un valor inválido desactiva las
trazas. Sin clave, sin SDK o con un fallo del SDK, la aplicación sigue funcionando;
los avisos locales no incluyen el texto de la excepción. La configuración del
cliente se guarda por proceso: reinicia después de cambiar las variables.
Para claves de organización, configura también `LANGSMITH_WORKSPACE_ID`.

En Docker, el SDK no forma parte de las imágenes por defecto. Para incluirlo,
configura `INSTALL_LANGSMITH=true` y reconstruye API y worker:

```sh
docker compose -f docker-compose.prod.yml build api worker
docker compose -f docker-compose.prod.yml up -d api worker
```

El build instala el lock opcional con hashes. `env_file: .env` ya permite pasar
la configuración a ambos servicios. La instalación del SDK y la activación de
tracing son dos decisiones separadas. El dashboard y el frontend no necesitan el SDK.
El lock opcional usa `requirements-api.lock` como restricción para conservar
las versiones existentes de las dependencias compartidas con el backend.

## Cobertura y privacidad

- FastAPI: una raíz `api.request` por petición, sin URL, método, headers, cuerpo,
  parámetros, ID del usuario, ID de petición ni contenido de la respuesta.
- Worker: mantenimiento, colas manuales y de alertas, sincronización manual,
  búsquedas de alertas, scraper periódico, outbox y envío de notificaciones.
  Los hijos se anidan mediante `ContextVar`, también al ejecutar servicios desde
  FastAPI. Cada tarea del scheduler crea su propia raíz.
- Next.js realiza peticiones Axios desde el navegador; Streamlit utiliza
  requests contra FastAPI. Sus operaciones quedan cubiertas por `api.request`.
  No se instrumentan sesiones, formularios, CV ni cookies y no se distribuyen
  claves al navegador. No hay propagación de cabeceras externas de LangSmith
  ni correlación persistente entre la petición que encola un trabajo y su ejecución.

Los nombres son constantes definidas por el desarrollador. Nunca se serializan
argumentos, resultados, objetos ORM, búsquedas, ofertas, destinos de avisos,
tokens o biografías. Inputs y outputs siempre son `{}`; además, el cliente los
oculta, junto con los metadatos que pueda añadir el SDK desde el entorno.
Las excepciones que escapan de una operación se registran como
`operation_failed`, sin mensaje ni traceback. No se añaden metadatos de usuario.
LangSmith recibe los identificadores técnicos del SDK, nombres fijos y tiempos.
El adaptador del cliente evita que el SDK añada variables del entorno después
del filtrado; depende de una extensión interna del SDK fijado en 0.4.58, cubierta
por una prueba real sin transporte de red. Revalida esa prueba al actualizarlo.
No pases información de usuario al nombre de un span. Las operaciones que
gestionan sus propios errores y retornan normalmente pueden aparecer como
correctas: consulta los registros de `ScraperRun` y del outbox para su resultado.
Esta integración no modifica los registros locales existentes.

La API y el worker vacían la cola del SDK al apagarse. Usan el envío en segundo
plano del SDK; el vaciado espera como máximo dos segundos y no bloquea el
event loop de FastAPI. Una terminación abrupta o un timeout puede perder las
últimas trazas. Se desactiva la replicación implícita del SDK para impedir que
variables globales cambien los destinos o añadan datos a las trazas. El timeout del
cliente es de un segundo por solicitud. Los fallos de observabilidad no deben
bloquear el procesamiento del negocio.

## Evaluaciones y pruebas

Ejecuta una evaluación determinista sin claves ni llamadas a LangSmith:

```sh
python -m scripts.evaluate_matching
pytest tests/test_tracing.py -q
ruff check .
```

Los siete casos sintéticos verifican términos, mayúsculas, aliases de campos,
descripciones, ubicación, modalidad y alertas inactivas. El comando retorna
código 1 si alguna predicción no coincide con la referencia. CI lo ejecuta
siempre con tracing y subida desactivados, y verifica el SDK opcional en otro paso.
Las pruebas verifican privacidad, excepciones, aislamiento concurrente, muestreo
y tolerancia a fallos del SDK.

Para crear un dataset y un experimento **con datos sintéticos únicamente**:

```sh
JOBRADAR_LANGSMITH_EVALUATIONS_ENABLED=true python -m scripts.evaluate_matching --upload
```

Requiere el SDK y `LANGSMITH_API_KEY`. Cada ejecución crea un dataset nuevo con
un nombre único; aplica la retención adecuada en LangSmith. No lee datos de
usuarios ni ofertas reales. La subida tiene un opt-in separado del tracing.
No se ejecuta automáticamente en CI ni requiere secretos de GitHub Actions.

Referencias del SDK: [RunTree](https://docs.langchain.com/langsmith/annotate-code),
[protección de datos](https://docs.langchain.com/langsmith/mask-inputs-outputs)
y [evaluaciones](https://docs.langchain.com/langsmith/evaluate-llm-application).
