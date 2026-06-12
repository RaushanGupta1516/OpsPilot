import json

from app.agents.state import IncidentState
from app.core.database import db
from app.core.config import settings
from datetime import datetime, timezone


async def postmortem_node(state: IncidentState) -> IncidentState:
    """
    generates a structured postmortem after incident is handled.
    only runs if an incident was actually created.
    """
    incident_id = state.get("incident_id")
    if not incident_id:
        print("[postmortem] no incident to generate postmortem for")
        return {**state, "postmortem_generated": False, "postmortem_id": None}

    print(f"[postmortem] generating postmortem for incident {incident_id}")

    # build timeline from causal chain + action taken
    timeline = []
    for event in state.get("causal_chain", []):
        timeline.append({"time": "T-0", "event": event})

    timeline.append({
        "time": "T+0",
        "event": f"OpsPilot detected anomaly — {state['anomaly_reason']}"
    })
    timeline.append({
        "time": "T+1",
        "event": f"Diagnosis: {state['root_cause']} (confidence: {state['confidence']:.0%})"
    })
    timeline.append({
        "time": "T+2",
        "event": f"Action: {state['action_taken']} — {state['action_status']}"
    })

    # get permanent fix recommendation from RAG patterns
    permanent_fix = _get_permanent_fix(state)
    code_snippet = _get_code_snippet(state)

   
    postmortem = await db.postmortem.create(
        data={
            "incident": {"connect": {"id": incident_id}},
            "timeline": json.dumps(timeline),
            "rootCauseAnalysis": state["root_cause"],
            "fixApplied": state["action_taken"],
            "permanentRecommendation": permanent_fix,
            "codeSnippet": code_snippet,
        }
    )

    # mark incident as resolved
    await db.incident.update(
        where={"id": incident_id},
        data={
            "status": "resolved",
            "resolvedAt": datetime.now(timezone.utc),
        }
    )

    print(f"[postmortem] generated postmortem {postmortem.id}")
    return {
        **state,
        "postmortem_generated": True,
        "postmortem_id": postmortem.id,
        "is_resolved": True,
    }


def _get_permanent_fix(state: IncidentState) -> str:
    patterns = state.get("rag_patterns", [])
    if patterns:
        top_pattern = patterns[0].get("pattern", {})
        fix_steps = top_pattern.get("fix_steps", [])
        if fix_steps:
            return " | ".join(fix_steps)

    # fallback based on recommended action
    action = state.get("recommended_action", "")
    if action == "restart_service":
        return "Investigate root cause of crash. Add health check endpoints. Consider auto-restart policies."
    elif action == "escalate":
        return "This is a recurring issue. Address the root cause permanently rather than restarting."
    return "Monitor the service and investigate logs for permanent resolution."


def _get_code_snippet(state: IncidentState) -> str:
    patterns = state.get("rag_patterns", [])
    if patterns:
        top_pattern = patterns[0].get("pattern", {})
        return top_pattern.get("code_snippet", "")
    return ""