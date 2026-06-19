from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional

from app.core.database import connect_db, disconnect_db
from app.core.config import settings
from app.api.apps import router as apps_router
from app.api.metrics import router as metrics_router
from app.api.rag import router as rag_router
from app.api.agent import router as agent_router
from app.rag.ingestor import ingest_knowledge_base
from app.core.websocket_manager import ws_manager
from app.services.baseline_service import update_baseline_progress, check_anomaly


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[opspilot] starting up in {settings.app_env} mode")
    await connect_db()
    await ingest_knowledge_base()
    yield
    await disconnect_db()
    print(f"[opspilot] shut down cleanly")


app = FastAPI(
    title="OpsPilot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "https://ops-pilot-gfgs.vercel.app",
    "https://*.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apps_router)
app.include_router(metrics_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# internal endpoints called by celery worker
class MetricBroadcast(BaseModel):
    app_id: str
    app_name: str
    metric: dict


class AgentTriggerInternal(BaseModel):
    app_id: str
    app_name: str
    app_url: str
    app_environment: str
    response_time_ms: Optional[int] = None
    error_rate: float = 0.0
    is_healthy: bool = True
    anomaly_reason: str = ""


class AnomalyCheckRequest(BaseModel):
    app_id: str
    response_time_ms: int
    error_rate: float
    is_healthy: bool


@app.post("/internal/broadcast-metric")
async def broadcast_metric(payload: MetricBroadcast):
    await ws_manager.broadcast_metric(payload.app_id, payload.app_name, payload.metric)

    is_healthy = payload.metric.get("is_healthy", True)
    message = payload.metric.get("message", "")
    await ws_manager.broadcast_health(payload.app_id, payload.app_name, is_healthy, message)

    return {"ok": True}


@app.post("/internal/check-anomaly")
async def check_anomaly_internal(payload: AnomalyCheckRequest):
    await update_baseline_progress(payload.app_id)

    if not payload.is_healthy:
        return {
            "is_anomaly": True,
            "reason": "service unreachable",
            "using_baseline": False,
        }

    result = await check_anomaly(
        payload.app_id,
        payload.response_time_ms,
        payload.error_rate,
    )
    return result


@app.post("/internal/trigger-agent")
async def trigger_agent_internal(payload: AgentTriggerInternal):
    from app.api.agent import trigger_agent, TriggerRequest
    req = TriggerRequest(
        app_id=payload.app_id,
        app_name=payload.app_name,
        app_url=payload.app_url,
        app_environment=payload.app_environment,
        response_time_ms=payload.response_time_ms,
        error_rate=payload.error_rate,
        is_healthy=payload.is_healthy,
        anomaly_reason=payload.anomaly_reason,
    )
    return await trigger_agent(req)


@app.get("/")
async def root():
    return {"status": "ok", "app": settings.app_name}


@app.get("/health")
async def health():
    return {"status": "healthy", "env": settings.app_env}