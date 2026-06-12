import httpx
import psutil
import time
from typing import Optional
from app.models.schemas import HealthCheckResult

REQUEST_TIMEOUT = 10.0


async def ping_app(app_id: str, app_name: str, url: str) -> HealthCheckResult:
    response_time_ms = None
    status_code = None
    is_healthy = False
    message = ""

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url)
        elapsed = time.monotonic() - start

        response_time_ms = int(elapsed * 1000)
        status_code = resp.status_code
        is_healthy = resp.status_code < 400
        message = "ok" if is_healthy else f"got status {resp.status_code}"

    except httpx.TimeoutException:
        message = "request timed out"
        is_healthy = False
    except httpx.ConnectError:
        message = "connection failed"
        is_healthy = False
    except Exception as e:
        message = f"unexpected error: {str(e)}"
        is_healthy = False

    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)

    return HealthCheckResult(
        app_id=app_id,
        app_name=app_name,
        is_healthy=is_healthy,
        response_time_ms=response_time_ms,
        status_code=status_code,
        error_rate=0.0 if is_healthy else 1.0,
        memory_mb=round(mem.used / 1024 / 1024, 2),
        cpu_percent=round(cpu, 2),
        message=message,
    )