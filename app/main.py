from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routers import auth, edge, web
from app.config import settings
from app.middleware.tls_enforcement import enforce_tls
from app.services.signaling_service import SignalingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Create singleton SignalingService
    app.state.signaling_service = SignalingService()
    yield
    # Shutdown: close all long-poll connections
    await app.state.signaling_service.close_all_connections()


app = FastAPI(
    title="UniFlow API",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add TLS enforcement middleware (if enabled)
if settings.enforce_tls:
    app.middleware("http")(enforce_tls)

# Mount routers with correct prefixes and tags
app.include_router(health_router, prefix="/api")
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(web.router, prefix="/api/v1", tags=["web"])
app.include_router(edge.router, prefix="/api/v1/edge", tags=["edge"])
