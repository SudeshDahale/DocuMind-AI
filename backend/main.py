from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes.upload import router
from routes.features import router as features_router
from core.logger import get_logger
from core.metrics import snapshot

log = get_logger("app")

app = FastAPI(title="DocuMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(features_router)


@app.get("/metrics")
def get_metrics():
    """Live latency + token usage summary."""
    return JSONResponse(content=snapshot())


@app.on_event("startup")
async def startup():
    log.info("DocuMind API is up", extra={"event": "server_started"})