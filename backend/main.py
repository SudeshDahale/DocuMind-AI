from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.upload import router
from routes.features import router as features_router
from routes.auth import router as auth_router
from core.logger import get_logger
from core.metrics import snapshot
from db import init_db
import os

log = get_logger("app")
app = FastAPI(title="DocuMind API")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "https://documind-ai-ecru.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)
app.include_router(features_router)


@app.get("/metrics")
def get_metrics():
    return JSONResponse(content=snapshot())


@app.on_event("startup")
async def startup():
    await init_db()
    log.info("DocuMind API is up", extra={"event": "server_started"})