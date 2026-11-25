from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.config import settings
from app.database import Base, engine
from app.routers.api import router

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV.lower() == "production":
        if (settings.SECRET_KEY == "change-this-secret-before-use"
                or "CHANGE_THIS" in settings.SECRET_KEY.upper()
                or "REPLACE" in settings.SECRET_KEY.upper()
                or len(settings.SECRET_KEY) < 32):
            raise RuntimeError(
                "Set a strong SECRET_KEY (at least 32 characters) before production startup."
            )
        origins = settings.cors_origins
        local_only = all(
            origin.startswith("http://localhost")
            or origin.startswith("http://127.0.0.1")
            for origin in origins
        )
        if not origins or local_only or any("*" in origin for origin in origins):
            raise RuntimeError(
                "Set CORS_ORIGINS to explicit trusted production HTTPS origins."
            )
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="REST API for the MediCare Appointment Booking System",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Flutter web development can use a dynamically assigned localhost port.
    # Production uses only the explicit CORS_ORIGINS allow-list.
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
        if settings.APP_ENV.lower() != "production"
        else None
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(router, prefix="/api/v1")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.APP_NAME,
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy"}

# Run: python -m uvicorn app.main:app --reload
