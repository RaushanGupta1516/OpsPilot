from app.core.database import db
from app.models.schemas import HealthCheckResult


async def store_metric(result: HealthCheckResult) -> None:
    try:
        await db.metric.create(
            data={
                "appId": result.app_id,
                "endpoint": "/",
                "responseTimeMs": result.response_time_ms,
                "statusCode": result.status_code,
                "errorRate": result.error_rate,
                "memoryMb": result.memory_mb,
                "cpuPercent": result.cpu_percent,
                "isHealthy": result.is_healthy,
            }
        )
    except Exception as e:
        print(f"[metrics] failed to store metric for {result.app_id}: {e}")


async def get_recent_metrics(app_id: str, limit: int = 50):
    metrics = await db.metric.find_many(
        where={"appId": app_id},
        order={"recordedAt": "desc"},
        take=limit,
    )
    return metrics


async def get_latest_metric(app_id: str):
    metric = await db.metric.find_first(
        where={"appId": app_id},
        order={"recordedAt": "desc"},
    )
    return metric