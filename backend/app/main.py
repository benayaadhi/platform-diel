"""Entry point FastAPI Platform-DIEL (Fase 2)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import auth, leaderboard, runs, strategies


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Platform-DIEL API",
    version="0.2.0",
    description="Marketplace strategi trading terverifikasi — backend Fase 2.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "diel-api", "version": app.version}


app.include_router(auth.router)
app.include_router(strategies.router)
app.include_router(runs.router)
app.include_router(leaderboard.router)
