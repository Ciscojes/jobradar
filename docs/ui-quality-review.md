# Revisión de interfaz y calidad — 6 de noviembre de 2026

## Alcance

Tablero y estadísticas de Next.js con etiquetas claras y menos decoración.
Las columnas ajustan su altura al contenido en móvil. Se retira la interfaz
Python heredada, sus dependencias, captura, servicio Docker y puerto.
El smoke test comprueba el frontend en el puerto 3000 con `--frontend-url`.

## Verificación

- Ruff y compilación de Python aprobados.
- 80 pruebas SQLite; cobertura de aplicación 80,67 %, umbral 60 % conservado.
- Auditoría de requisitos Python sin vulnerabilidades.
- Frontend: lint, build y auditoría aprobados tras actualizar dependencias.
- Tablero y estadísticas revisados a 320, 390 y 1440 px con respuestas API
  sintéticas exclusivamente locales; sin desbordamiento horizontal.
- CI conserva pruebas PostgreSQL, migraciones, Compose e imágenes; se añade
  un trabajo explícito para lint, auditoría y compilación del frontend.

## Dependencias

Actualización compatible de Next.js 15 y dependencias transitivas vulnerables.
Parser y plugin TypeScript compatibles con ESLint 9. La resolución de minimatch
se limita a typescript-estree y se verifica con lint.

## Límites

Las capturas locales no acreditan las integraciones Adzuna o Telegram.
PostgreSQL, Compose e imágenes deben aprobarse en la ejecución remota del PR #3.
