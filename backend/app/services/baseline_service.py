from app.core.database import db
from datetime import datetime, timezone
import statistics


async def update_baseline_progress(app_id: str) -> bool:
    """
    increments baseline observation hours counter.
    returns True if baseline is now ready (48h complete)
    """
    app = await db.app.find_unique(where={"id": app_id})
    if not app:
        return False

    if app.baselineReady:
        return True

    # each monitoring cycle is 30 seconds, so 120 cycles = 1 hour
    # we track in hours for simplicity
    new_hours = app.baselineHours + 1

    # 48 hours * 120 cycles = 5760 cycles total
    # but we increment by 1 each cycle and check against 5760
    baseline_ready = new_hours >= 5760

    await db.app.update(
        where={"id": app_id},
        data={
            "baselineHours": new_hours,
            "baselineReady": baseline_ready,
        }
    )

    if baseline_ready:
        print(f"[baseline] app {app_id} baseline observation complete")
        await calculate_baselines(app_id)

    return baseline_ready


async def calculate_baselines(app_id: str):
    """
    calculates mean and std dev for each metric per hour of day.
    runs once after 48h observation period completes.
    """
    print(f"[baseline] calculating baselines for app {app_id}")

    metrics = await db.metric.find_many(
        where={"appId": app_id},
        order={"recordedAt": "asc"},
    )

    if len(metrics) < 10:
        print(f"[baseline] not enough data for app {app_id}")
        return

    # group by hour of day
    hourly_response_times: dict = {}
    hourly_error_rates: dict = {}

    for m in metrics:
        hour = m.recordedAt.hour
        if hour not in hourly_response_times:
            hourly_response_times[hour] = []
            hourly_error_rates[hour] = []

        if m.responseTimeMs:
            hourly_response_times[hour].append(m.responseTimeMs)
        hourly_error_rates[hour].append(m.errorRate)

    # store baselines for each hour
    for hour in hourly_response_times:
        rt_values = hourly_response_times[hour]
        er_values = hourly_error_rates[hour]

        if len(rt_values) >= 2:
            await db.baseline.upsert(
                where={
                    "appId_endpoint_metricType_hourOfDay": {
                        "appId": app_id,
                        "endpoint": "/",
                        "metricType": "response_time",
                        "hourOfDay": hour,
                    }
                },
                data={
                    "create": {
                        "appId": app_id,
                        "endpoint": "/",
                        "metricType": "response_time",
                        "hourOfDay": hour,
                        "mean": statistics.mean(rt_values),
                        "stdDev": statistics.stdev(rt_values) if len(rt_values) > 1 else 0,
                        "sampleCount": len(rt_values),
                    },
                    "update": {
                        "mean": statistics.mean(rt_values),
                        "stdDev": statistics.stdev(rt_values) if len(rt_values) > 1 else 0,
                        "sampleCount": len(rt_values),
                    }
                }
            )

    print(f"[baseline] baselines stored for app {app_id}")


async def check_anomaly(app_id: str, response_time_ms: int, error_rate: float) -> dict:
    """
    compares current metric against learned baseline.
    returns anomaly info if detected.
    """
    current_hour = datetime.now(timezone.utc).hour

    baseline = await db.baseline.find_first(
        where={
            "appId": app_id,
            "metricType": "response_time",
            "hourOfDay": current_hour,
        }
    )

    if not baseline:
        # no baseline yet - use hardcoded defaults
        is_anomaly = response_time_ms > 3000 or error_rate > 0.05
        return {
            "is_anomaly": is_anomaly,
            "reason": "exceeded default threshold (3000ms / 5% error rate)",
            "using_baseline": False,
        }

    # mean + 2 std deviations = anomaly threshold
    threshold = baseline.mean + (2 * baseline.stdDev)
    is_anomaly = response_time_ms > threshold or error_rate > 0.05

    return {
        "is_anomaly": is_anomaly,
        "threshold_ms": round(threshold, 0),
        "current_ms": response_time_ms,
        "reason": f"exceeded learned threshold of {round(threshold)}ms" if is_anomaly else "within normal range",
        "using_baseline": True,
    }