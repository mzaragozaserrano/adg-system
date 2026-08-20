import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.api.routers import auth, layout, presentations, transcriber
from src.db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando API ADG (health=%s)", settings.api_url)
    init_db()
    yield


app = FastAPI(title="Validador ADG API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(presentations.router)
app.include_router(transcriber.router)
app.include_router(layout.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}",
        },
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "adg-system",
        "version": "2026-08-20-v7",
        "allowed_email_domains": settings.resolved_allowed_email_domains,
        "allowed_emails": settings.resolved_allowed_emails,
    }
