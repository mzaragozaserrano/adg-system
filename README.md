# Validador de Identidad ADG — v2.0

Herramienta interna para empleados de ADG Media Group: valida presentaciones PDF y Google Slides contra el manual de identidad corporativa, corrige errores en Slides y exporta informes.

## Arranque rápido

```bash
# Terminal 1 — API backend
chmod +x run-api.sh run-frontend.sh
./run-api.sh

# Terminal 2 — Frontend web
./run-frontend.sh
```

Abre `http://localhost:5173` e inicia sesión con tu cuenta Google corporativa.

## Configuración

1. Copia `.env.example` a `.env`
2. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
3. Habilita Google Slides API y Google Drive API
4. Crea credenciales OAuth 2.0 (tipo **Aplicación web**)
5. Añade `http://localhost:8000/auth/google/callback` como URI de redirección
6. Configura `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en `.env`

## Funcionalidades

| Función | PDF | Google Slides |
|---------|-----|---------------|
| Validar identidad ADG | Sí | Sí |
| Informe filtrable | Sí | Sí |
| Corrección automática | No | Sí (copia en Drive) |
| Exportar corregido | — | PDF / PPTX |
| Historial por usuario | Sí | Sí |
| Informe PDF descargable | Sí | Sí |

## CLI

```bash
PYTHONPATH=. python scripts/validate.py pdf docs/samples/plantilla_base_adg.pdf
PYTHONPATH=. python scripts/validate.py slides PRESENTATION_ID --json
```

## Streamlit (legacy local)

La interfaz Streamlit original sigue disponible para desarrollo local sin autenticación:

```bash
./run.sh
```

## Estructura

```
src/
  api/              # FastAPI (auth, validación, corrección, historial)
  auth/             # OAuth Google + JWT
  db/               # Modelos SQLAlchemy
  fixers/           # Motor de corrección Slides
  validators/       # Validación PDF y Slides
  services/         # Informes PDF, miniaturas
frontend/           # React + Vite
docs/manual_uso_equipo.md
```

## Despliegue con Docker

```bash
docker compose up --build
```

## Despliegue en producción (Vercel + API)

La **interfaz web** se publica en [Vercel](https://vercel.com/) (carpeta `frontend/`). La **API FastAPI** debe alojarse aparte (Render, Railway, Docker, etc.).

Guía paso a paso: [docs/deploy-vercel.md](docs/deploy-vercel.md)

Resumen rápido:

1. Despliega la API (`render.yaml` incluido) y anota su URL.
2. En Vercel: Root Directory = `frontend`, variable `VITE_API_URL` = URL de la API.
3. Configura OAuth en Google Cloud con las URLs de producción.

## Documentación

- [Manual de uso para el equipo](docs/manual_uso_equipo.md)
- [SDD](docs/SDD_Validador_ADG.md)
- [Roadmap](ROADMAP.md)
