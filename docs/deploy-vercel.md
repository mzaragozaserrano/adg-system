# Despliegue en Vercel (frontend) + API

La interfaz web (React + Vite) se publica en **Vercel**. El backend **FastAPI** debe desplegarse por separado (Render, Railway, Fly.io, VPS, etc.) porque usa OAuth, SQLite y Google APIs de forma persistente.

## Arquitectura

```
Usuario → Vercel (frontend estático)
              ↓ VITE_API_URL
         API FastAPI (Render / Railway / Docker)
              ↓
         Google Slides / Drive
```

## 1. Desplegar la API

### Opción A — Render (recomendada, incluye `render.yaml`)

1. Sube el repositorio a GitHub.
2. En [Render](https://render.com/) → **New** → **Blueprint** y conecta el repo (usa `render.yaml`).
3. Configura las variables de entorno (ver sección [Variables](#variables-de-entorno)).
4. Anota la URL pública, por ejemplo `https://adg-system-api.onrender.com`.

### Opción B — Docker en cualquier servidor

```bash
docker compose up --build -d
```

Expón el puerto `8000` con HTTPS (nginx, Caddy, etc.).

## 2. Desplegar el frontend en Vercel

1. En [Vercel](https://vercel.com/) → **Add New** → **Project**.
2. Importa el repositorio de GitHub.
3. Configuración del proyecto:

| Campo | Valor |
|-------|--------|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm ci` |

4. Variables de entorno en Vercel:

| Variable | Ejemplo |
|----------|---------|
| `VITE_API_URL` | `https://adg-system-api.onrender.com` |
| `VITE_GOOGLE_API_KEY` | API key **tipo aplicación web** (misma que `GOOGLE_API_KEY`) |
| `VITE_GOOGLE_APP_ID` | Número de proyecto GCP (mismo que `GOOGLE_APP_ID`) |

`VITE_GOOGLE_API_KEY` y `VITE_GOOGLE_APP_ID` son **obligatorias en Vercel**: el Picker se ejecuta en el navegador del dominio de Vercel, no en Render.

5. **Deploy**.

Tras el primer deploy tendrás una URL como `https://adg-system.vercel.app`.

## 3. Google Cloud Console

En tu proyecto OAuth (tipo **Aplicación web**):

**URIs de redirección autorizados**

- `https://TU-API.onrender.com/auth/google/callback`

**Orígenes JavaScript autorizados** (cliente OAuth Web)

- `https://tu-proyecto.vercel.app`
- `http://localhost:5173` (desarrollo local)

### API key para Google Picker (error «developer key is invalid»)

El selector de Drive usa **Google Picker** en el frontend. Si falla con *The API developer key is invalid*:

1. En GCP → **APIs y servicios** → **Biblioteca** → activa **Google Picker API**.
2. **Credenciales** → crea una **clave de API** → tipo **Aplicaciones web** (no «IP» ni «servidor»).
3. Restringe la key por **referentes HTTP** e incluye:
   - `https://tu-proyecto.vercel.app/*`
   - `https://*.vercel.app/*` (previews; Google no admite comodín en un solo entry — añade cada preview si hace falta)
   - `http://localhost:5173/*` (local)
4. El **número de proyecto** (`GOOGLE_APP_ID` / `VITE_GOOGLE_APP_ID`) debe ser el de el mismo proyecto GCP que el OAuth client.
5. En **Vercel**, define `VITE_GOOGLE_API_KEY` y `VITE_GOOGLE_APP_ID` (no basta con tenerlas solo en Render).

### Evitar «configuración avanzada / sitio no seguro»

Esa pantalla **no la genera ADG**: la muestra Google porque la app OAuth está en modo **Prueba** y pide permisos sensibles (Drive/Slides). No se quita con un cambio de código.

**Lo que hay que hacer en Google Cloud (una sola vez):**

1. Entra en [Google Cloud Console](https://console.cloud.google.com/) con una cuenta admin de `adgravity.com`.
2. Elige el proyecto de OAuth → **APIs y servicios** → **Pantalla de consentimiento de OAuth**.
3. En **Tipo de usuario** elige **Interno**.
   - El proyecto GCP tiene que pertenecer a la organización Google Workspace de ADG.
   - Si el tipo Interno no aparece, el proyecto está en una cuenta personal: hay que crear/usar un proyecto de la organización.
4. Guarda.

Con tipo **Interno**, los empleados `@adgravity.com` dejan de ver «esta app no está verificada» y no hace falta «Configuración avanzada». Tampoco hace falta la verificación pública de Google.

**No sirve** publicar la app como Externa en Prueba: Drive (`drive.readonly`) es un alcance restringido y Google seguirá mostrando la advertencia hasta verificar la app (proceso largo). Para una herramienta interna, **Interno** es la solución correcta.

Si alguien sigue viendo la advertencia: confirma que entra con `@adgravity.com` (no Gmail personal) y que el cliente OAuth es el del mismo proyecto marcado como Interno.

## Variables de entorno

### API (Render / servidor)

| Variable | Descripción |
|----------|-------------|
| `FRONTEND_URL` | URL de Vercel, p. ej. `https://adg-system.vercel.app` |
| `API_URL` | URL pública de la API |
| `GOOGLE_CLIENT_ID` | OAuth Google |
| `GOOGLE_CLIENT_SECRET` | OAuth Google |
| `GOOGLE_REDIRECT_URI` | `https://TU-API/auth/google/callback` |
| `GOOGLE_API_KEY` | API key (picker de Drive) |
| `GOOGLE_APP_ID` | Número de proyecto Google |
| `SECRET_KEY` | Clave aleatoria larga (JWT) |
| `TOKEN_ENCRYPTION_KEY` | Clave Fernet para tokens Google |
| `ALLOWED_EMAIL_DOMAINS` | `adgravity.com` (varios dominios separados por coma) |
| `DATABASE_URL` | `sqlite:////app/data/validador.db` (con disco en Render) |
| `CORS_ORIGINS` | Opcional: URLs extra separadas por coma |

**Importante (Render):** si en el dashboard de Render existe la variable legacy `ALLOWED_EMAIL_DOMAIN` con un valor antiguo (p. ej. `adgmediagroup.com`), **elimínala**. La app usa `ALLOWED_EMAIL_DOMAINS`. Tras el deploy, comprueba `GET /health` y verifica `allowed_email_domains`.

### Vercel (frontend)

| Variable | Descripción |
|----------|-------------|
| `VITE_API_URL` | URL pública de la API (sin `/api` al final) |
| `VITE_GOOGLE_API_KEY` | API key browser para Google Picker (referrer = dominio Vercel) |
| `VITE_GOOGLE_APP_ID` | Número de proyecto GCP |

## Comprobar el despliegue

1. `https://TU-API/health` → debe incluir `"allowed_email_domains":["adgravity.com"]`
2. Abre la URL de Vercel → pantalla de login.
3. Inicia sesión con Google → vuelve a `/auth/callback` con token.
4. Valida una presentación de prueba.

## Previews de Vercel

CORS acepta automáticamente `https://*.vercel.app`. En previews, define también `VITE_API_URL` apuntando a la API de staging o producción.

## CLI (opcional)

Con [Vercel CLI](https://vercel.com/docs/cli):

```bash
cd frontend
npm ci
vercel login
vercel --prod
```

Configura `VITE_API_URL` en el dashboard de Vercel o con `vercel env add`.
