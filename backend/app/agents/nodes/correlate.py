from app.agents.state import IncidentState
from app.core.database import db
from datetime import datetime, timezone, timedelta
import hashlib
import json


async def correlate_node(state: IncidentState) -> IncidentState:
    """
    checks if this is a duplicate incident and builds causal chain.
    dedup window: 5 minutes. if same app had same issue recently, skip.
    """
    print(f"[correlate] checking app {state['app_name']}")

    app_id = state["app_id"]
    trigger = state["trigger_metric"]

    # pull last 30 mins of metrics for causal chain
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    recent = await db.metric.find_many(
        where={
            "appId": app_id,
            "recordedAt": {"gte": since},
        },
        order={"recordedAt": "asc"},
        take=60,
    )

    recent_dicts = []
    for m in recent:
        recent_dicts.append({
            "response_time_ms": m.responseTimeMs,
            "error_rate": m.errorRate,
            "is_healthy": m.isHealthy,
            "recorded_at": m.recordedAt.isoformat(),
        })

    # build causal chain from metric history
    causal_chain = _build_causal_chain(recent_dicts, trigger)

    # dedup check - look for open incidents in last 5 mins
    dedup_since = datetime.now(timezone.utc) - timedelta(minutes=5)
    existing = await db.incident.find_first(
        where={
            "appId": app_id,
            "status": "open",
            "startedAt": {"gte": dedup_since},
        },
        order={"startedAt": "desc"},
    )

    if existing:
        print(f"[correlate] duplicate incident detected — skipping")
        return {
            **state,
            "is_duplicate": True,
            "existing_incident_id": existing.id,
            "causal_chain": causal_chain,
            "recent_metrics": recent_dicts,
            "should_act": False,
        }

    print(f"[correlate] new incident. causal chain: {len(causal_chain)} events")
    return {
        **state,
        "is_duplicate": False,
        "existing_incident_id": None,
        "causal_chain": causal_chain,
        "recent_metrics": recent_dicts,
        "should_act": True,
    }


def _build_causal_chain(metrics: list, trigger: dict) -> list:
    if not metrics:
        return ["No historical data available"]

    chain = []

    # look for patterns in the last 30 mins
    slow_count = sum(1 for m in metrics if m.get("response_time_ms") and m["response_time_ms"] > 2000)
    error_count = sum(1 for m in metrics if m.get("error_rate") and m["error_rate"] > 0)
    unhealthy_count = sum(1 for m in metrics if not m.get("is_healthy"))

    if slow_count > 3:
        chain.append(f"Response time elevated in {slow_count} of last {len(metrics)} checks")

    if error_count > 0:
        chain.append(f"Errors detected in {error_count} recent checks")

    if unhealthy_count > 0:
        chain.append(f"Service reported unhealthy {unhealthy_count} times")

    current_rt = trigger.get("response_time_ms")
    if current_rt:
        chain.append(f"Current response time: {current_rt}ms")

    if not chain:
        chain.append("Sudden degradation — no prior warning signals")

    return chain