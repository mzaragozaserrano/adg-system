# Manual de uso — Validador ADG v2.0

## Acceso

1. Abre la aplicación web (por defecto `http://localhost:5173`).
2. Pulsa **Iniciar sesión con Google** con tu cuenta corporativa `@adgravity.com`.
3. Autoriza el acceso a Google Slides y Drive cuando se solicite.

## Validar un PDF

1. Ve a la pestaña **PDF**.
2. Selecciona el archivo PDF de la presentación.
3. Revisa el informe de errores por diapositiva.
4. Descarga el informe en JSON o PDF.

Los PDF solo se validan; para corregir automáticamente, trabaja la presentación en Google Slides.

## Validar Google Slides

1. Ve a la pestaña **Google Slides**.
2. Pulsa **Seleccionar desde Drive** y elige la presentación en el selector de Google.
3. Si el archivo no es de Google Slides, la app mostrará un error.
4. También puedes pegar la URL manualmente y pulsar **Validar por URL**.
5. Revisa errores graves y posibles, filtrados por severidad y categoría.

### Configurar selector de Drive (Google Picker)

En Google Cloud Console, además del OAuth:

1. Activa **Google Picker API**.
2. Crea una **API key** restringida a Picker y al referrer `http://localhost:5173/*`.
3. Añade en `.env`:
   - `GOOGLE_API_KEY` — la API key
   - `GOOGLE_APP_ID` — número de proyecto GCP (ej. `724095308816`)

## Corregir errores en Slides

1. Tras validar una presentación de Slides, marca los errores corregibles que quieras aplicar.
2. Pulsa **Corregir seleccionados** o **Corregir todos los corregibles**.
3. Se crea una copia corregida en tu Drive (el original no se modifica).
4. Abre la copia en Google Slides o descárgala en PDF/PPTX.

## Historial

El panel **Historial reciente** muestra validaciones anteriores. Pulsa una entrada para volver a ver su informe.

## Arranque local (desarrollo)

```bash
# Terminal 1 — API
./run-api.sh

# Terminal 2 — Frontend
./run-frontend.sh
```

## Variables de entorno

Copia `.env.example` a `.env` y configura:

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — credenciales OAuth Web de Google Cloud
- `GOOGLE_REDIRECT_URI` — `http://localhost:8000/auth/google/callback`
- `ALLOWED_EMAIL_DOMAINS` — dominios corporativos permitidos (separados por coma)
- `SECRET_KEY` — clave para tokens de sesión
- `FRONTEND_URL` — URL del frontend (`http://localhost:5173`)

## CLI (sin interfaz web)

```bash
PYTHONPATH=. python scripts/validate.py pdf docs/samples/plantilla_base_adg.pdf
PYTHONPATH=. python scripts/validate.py slides PRESENTATION_ID --json
```
