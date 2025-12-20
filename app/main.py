from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import refresh_active_sites

from app.endpoints.register import router as register_router
from app.endpoints.track import router as track_router

from app.endpoints.dashboards.context import router as dashboards_context_router
from app.endpoints.dashboards.metrics import router as dashboards_metrics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await refresh_active_sites()
    yield


app = FastAPI(
    title="AI Scan API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/track")
async def track_get_stub():
    return {
        "status": "ok",
        "message": "Tracking endpoint expects POST requests only.",
    }

app.include_router(register_router)
app.include_router(track_router)

# dashboards
app.include_router(dashboards_context_router)
app.include_router(dashboards_metrics_router)
