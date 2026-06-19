import asyncio
import httpx
from app.workers.celery_app import celery_app

import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# fallback thresholds - used only until an app has a learned baseline
RESPONSE_TIME_THRESHOLD = 3000  # ms
ERROR_RATE_THRESHOLD = 0.05


@celery_app.task(name="app.workers.monitor_task.run_monitoring_cycle")
def run_monitoring_cycle():
    asyncio.run(_async_monitoring_cycle())


async def _async_monitoring_cycle():
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(f"{API_BASE}/apps/")
            if resp.status_code != 200:
                print(f"[monitor] failed to get apps: {resp.status_code}")
                return

            apps = resp.json()
            if not apps:
                print("[monitor] no active apps")
                return

            print(f"[monitor] checking {len(apps)} apps")

            for app in apps:
                try:
                    check_resp = await client.post(
                        f"{API_BASE}/apps/{app['id']}/check"
                    )

                    if check_resp.status_code != 200:
                        continue

                    result = check_resp.json()

                    # broadcast metric update via websocket
                    await client.post(
                        f"{API_BASE}/internal/broadcast-metric",
                        json={
                            "app_id": app["id"],
                            "app_name": app["name"],
                            "metric": result,
                        }
                    )

                    is_healthy = result.get("is_healthy", True)
                    response_time = result.get("response_time_ms") or 0
                    error_rate = result.get("error_rate", 0)

                    # ask baseline service whether this is an anomaly —
                    # uses learned per-hour baselines once an app has 48h of
                    # data, falls back to fixed thresholds until then
                    anomaly_resp = await client.post(
                        f"{API_BASE}/internal/check-anomaly",
                        json={
                            "app_id": app["id"],
                            "response_time_ms": response_time,
                            "error_rate": error_rate,
                            "is_healthy": is_healthy,
                        }
                    )

                    if anomaly_resp.status_code == 200:
                        anomaly_data = anomaly_resp.json()
                        anomaly_detected = anomaly_data.get("is_anomaly", False)
                        reason = anomaly_data.get("reason", "anomaly detected")
                        using_baseline = anomaly_data.get("using_baseline", False)
                    else:
                        # baseline service unreachable - fall back to inline check
                        anomaly_detected = (
                            not is_healthy or
                            response_time > RESPONSE_TIME_THRESHOLD or
                            error_rate > ERROR_RATE_THRESHOLD
                        )
                        reason = _build_anomaly_reason(is_healthy, response_time, error_rate)
                        using_baseline = False

                    if anomaly_detected:
                        tag = "[baseline]" if using_baseline else "[default]"
                        print(f"[monitor] ⚠️ {tag} anomaly on {app['name']}: {reason}")

                        # trigger agent
                        await client.post(
                            f"{API_BASE}/internal/trigger-agent",
                            json={
                                "app_id": app["id"],
                                "app_name": app["name"],
                                "app_url": app["url"],
                                "app_environment": app["environment"],
                                "response_time_ms": response_time,
                                "error_rate": error_rate,
                                "is_healthy": is_healthy,
                                "anomaly_reason": reason,
                            }
                        )
                    else:
                        print(f"[monitor] ✅ {app['name']} — {response_time}ms")

                except Exception as e:
                    print(f"[monitor] error on {app['name']}: {e}")

    except Exception as e:
        print(f"[monitor] cycle failed: {e}")


def _build_anomaly_reason(is_healthy: bool, response_time: int, error_rate: float) -> str:
    reasons = []
    if not is_healthy:
        reasons.append("service unreachable")
    if response_time > RESPONSE_TIME_THRESHOLD:
        reasons.append(f"response time {response_time}ms exceeds {RESPONSE_TIME_THRESHOLD}ms threshold")
    if error_rate > ERROR_RATE_THRESHOLD:
        reasons.append(f"error rate {error_rate:.0%} exceeds 5% threshold")
    return " | ".join(reasons) if reasons else "anomaly detected"