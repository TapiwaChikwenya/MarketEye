"""
Main FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, users, assets, watchlists, alerts, portfolio

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(assets.router, prefix=f"{settings.API_V1_PREFIX}/assets", tags=["Assets"])
app.include_router(watchlists.router, prefix=f"{settings.API_V1_PREFIX}/watchlists", tags=["Watchlists"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"])
app.include_router(portfolio.router, prefix=f"{settings.API_V1_PREFIX}/portfolio", tags=["Portfolio"])


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
