from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routers import auth, edge, web
from app.config import settings

app = FastAPI(
    title="UniFlow API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers with correct prefixes and tags
app.include_router(health_router, prefix="/api")
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(web.router, prefix="/api/v1", tags=["web"])
app.include_router(edge.router, prefix="/api/v1/edge", tags=["edge"])
