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

5. **Deploy**.

Tras el primer deploy tendrás una URL como `https://adg-system.vercel.app`.

## 3. Google Cloud Console

En tu proyecto OAuth (tipo **Aplicación web**):

**URIs de redirección autorizados**

- `https://TU-API.onrender.com/auth/google/callback`

**Orígenes JavaScript autorizados** (para el picker de Drive)

- `https://tu-proyecto.vercel.app`
- `https://tu-proyecto-*.vercel.app` (si usas previews; Google no admite comodines — añade cada dominio de preview que uses o usa solo producción)

### Publicar OAuth para que cualquier `@adgravity.com` pueda entrar

Si al iniciar sesión aparece *"no ha completado la verificación de Google"* o *"solo los testers pueden probarlo"*, la pantalla de consentimiento OAuth está en modo **Prueba (Testing)**. Eso no se arregla en Vercel ni en Render: hay que cambiarlo en Google Cloud Console.

**Opción recomendada — App interna (Google Workspace)**

Si `adgravity.com` es un dominio de Google Workspace y el proyecto GCP pertenece a esa organización:

1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs y servicios** → **Pantalla de consentimiento de OAuth**.
2. En **Tipo de usuario**, elige **Interno** (solo usuarios de tu organización).
3. Guarda. No hace falta verificación de Google ni lista de testers: cualquier cuenta `@adgravity.com` de la organización puede autenticarse.

**Opción alternativa — Publicar en producción**

Si el proyecto GCP no puede ser interno (cuenta personal u otra organización):

1. **Pantalla de consentimiento de OAuth** → revisa que el dominio autorizado incluya `adgravity.com`.
2. Pulsa **Publicar aplicación** (cambiar de *Prueba* a *En producción*).
3. Los scopes de Drive y Slides pueden exigir **verificación de Google** (formulario, varios días). Hasta que aprueben, Google puede limitar usuarios o mostrar advertencias.

**Solución temporal (solo mientras está en Prueba)**

En la misma pantalla, sección **Usuarios de prueba**, añade cada correo que necesite acceder (p. ej. `lauza.zaragoza@adgravity.com`). Máximo 100 usuarios en modo Prueba.

Tras cambiar el estado de la app OAuth, no hace falta redesplegar la API: el cambio es inmediato en Google.

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
