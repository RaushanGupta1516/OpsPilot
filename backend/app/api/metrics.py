from fastapi import APIRouter, HTTPException
from app.services.metrics_service import get_recent_metrics, get_latest_metric
from app.core.database import db
from typing import Optional

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/anomalies")
async def get_anomalies(app_id: Optional[str] = None, limit: int = 50):
    try:
        where: dict = {"isHealthy": False}
        if app_id:
            where["appId"] = app_id
        metrics = await db.metric.find_many(
            where=where,
            include={"app": True},
            order={"recordedAt": "desc"},
            take=limit,
        )
        # shape it so frontend anomaly feed can render it
        result = []
        for m in metrics:
            result.append({
                "id": m.id,
                "appId": m.appId,
                "app": m.app,
                "metricType": "health_check",
                "severity": "high" if m.statusCode and m.statusCode >= 500 else "medium",
                "value": m.responseTimeMs or 0,
                "baseline": 0,
                "deviation": 0,
                "description": f"Unhealthy response — status {m.statusCode}, response time {m.responseTimeMs}ms",
                "timestamp": m.recordedAt.isoformat(),
                "incidentId": None,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{app_id}")
async def get_metrics(app_id: str, limit: int = 50):
    metrics = await get_recent_metrics(app_id, limit)
    if not metrics:
        raise HTTPException(status_code=404, detail="no metrics found for this app")
    return metrics


@router.get("/{app_id}/latest")
async def get_latest(app_id: str):
    metric = await get_latest_metric(app_id)
    if not metric:
        raise HTTPException(status_code=404, detail="no metrics found for this app")
    return metric