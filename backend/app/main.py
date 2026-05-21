"""
Main FastAPI application.
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, users, assets, watchlists, alerts, portfolio, public, tracked, notifications, admin
from app.db.base import Base, engine
import app.models  # Import all models to register them
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - create tables on startup."""
    app.state.started_at = time.time()
    logger.info("Creating database tables if they don't exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    # Cleanup on shutdown if needed


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS (explicit origins + optional LAN regex in development)
_cors_regex = None
if settings.DEBUG and settings.CORS_ALLOW_LAN_ORIGINS:
    # Match http://<private-or-loopback host>:<port> so phones/tablets on the same Wi‑Fi work.
    # Includes mDNS (.local) and IPv4 link-local (169.254.x.x) for hotspot / Bonjour cases.
    _cors_regex = (
        r"http://("
        r"localhost|127\.0\.0\.1"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r"|169\.254\.\d{1,3}\.\d{1,3}"
        r"|[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.local"
        r"):\d+$"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(public.router, prefix=f"{settings.API_V1_PREFIX}/public", tags=["Public"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(assets.router, prefix=f"{settings.API_V1_PREFIX}/assets", tags=["Assets"])
app.include_router(watchlists.router, prefix=f"{settings.API_V1_PREFIX}/watchlists", tags=["Watchlists"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"])
app.include_router(portfolio.router, prefix=f"{settings.API_V1_PREFIX}/portfolio", tags=["Portfolio"])
app.include_router(tracked.router, prefix=f"{settings.API_V1_PREFIX}/tracked", tags=["Tracked Assets"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to MarketEye API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
