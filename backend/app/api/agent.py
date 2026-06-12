from fastapi import APIRouter, HTTPException
from app.agents.graph import opspilot_graph
from app.agents.state import IncidentState
from app.core.websocket_manager import ws_manager
from app.core.database import db
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(prefix="/agent", tags=["agent"])


class TriggerRequest(BaseModel):
    app_id: str
    app_name: str
    app_url: str
    app_environment: str
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_rate: float = 0.0
    is_healthy: bool = True
    anomaly_reason: str = "manual trigger"


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


@router.post("/trigger")
async def trigger_agent(payload: TriggerRequest):
    thread_id = str(uuid.uuid4())

    await ws_manager.broadcast_agent_event(
        "agent_started",
        payload.app_name,
        {"reason": payload.anomaly_reason, "thread_id": thread_id}
    )

    initial_state: IncidentState = {
        "app_id": payload.app_id,
        "app_name": payload.app_name,
        "app_url": payload.app_url,
        "app_environment": payload.app_environment,
        "trigger_metric": {
            "response_time_ms": payload.response_time_ms,
            "status_code": payload.status_code,
            "error_rate": payload.error_rate,
            "is_healthy": payload.is_healthy,
        },
        "anomaly_reason": payload.anomaly_reason,
        "is_duplicate": False,
        "existing_incident_id": None,
        "causal_chain": [],
        "recent_metrics": [],
        "severity": 0,
        "root_cause": "",
        "confidence": 0.0,
        "recommended_action": "",
        "rag_patterns": [],
        "action_taken": "",
        "action_status": "",
        "human_approved": None,
        "incident_id": None,
        "postmortem_generated": False,
        "postmortem_id": None,
        "should_act": True,
        "is_resolved": False,
        "error": None,
    }

    config = {"configurable": {"thread_id": thread_id}}

    result = await opspilot_graph.ainvoke(initial_state, config=config)

    state_snapshot = opspilot_graph.get_state(config)
    is_interrupted = len(state_snapshot.next) > 0

    if is_interrupted:
        await ws_manager.broadcast_approval_request(thread_id, {
            "app_name": payload.app_name,
            "severity": result.get("severity"),
            "root_cause": result.get("root_cause"),
            "confidence": result.get("confidence"),
            "recommended_action": result.get("recommended_action"),
        })

    if result.get("is_duplicate"):
        await ws_manager.broadcast_agent_event(
            "duplicate_incident",
            payload.app_name,
            {"message": "duplicate incident detected — skipping"}
        )

    return {
        "thread_id": thread_id,
        "status": "awaiting_approval" if is_interrupted else "completed",
        "severity": result.get("severity"),
        "root_cause": result.get("root_cause"),
        "confidence": result.get("confidence"),
        "recommended_action": result.get("recommended_action"),
        "incident_id": result.get("incident_id"),
        "is_duplicate": result.get("is_duplicate"),
    }


@router.post("/resume")
async def resume_agent(payload: ResumeRequest):
    from langgraph.types import Command

    config = {"configurable": {"thread_id": payload.thread_id}}

    result = await opspilot_graph.ainvoke(
        Command(resume={"approved": payload.approved}),
        config=config,
    )

    await ws_manager.broadcast_agent_event(
        "incident_resolved" if result.get("is_resolved") else "action_rejected",
        result.get("app_name", "unknown"),
        {
            "action_taken": result.get("action_taken"),
            "action_status": result.get("action_status"),
            "postmortem_id": result.get("postmortem_id"),
        }
    )

    return {
        "thread_id": payload.thread_id,
        "action_status": result.get("action_status"),
        "action_taken": result.get("action_taken"),
        "human_approved": result.get("human_approved"),
        "postmortem_id": result.get("postmortem_id"),
        "is_resolved": result.get("is_resolved"),
    }


# ── Read endpoints for frontend ───────────────────────────────────────────

@router.get("/incidents")
async def list_incidents(app_id: Optional[str] = None):
    try:
        where = {"appId": app_id} if app_id else {}
        incidents = await db.incident.find_many(
            where=where,
            include={"app": True, "actions": True, "postmortem": True},
            order={"startedAt": "desc"},
        )
        result = []
        for inc in incidents:
            result.append({
                "id": inc.id,
                "appId": inc.appId,
                "app": inc.app,
                "status": inc.status.value,
                "summary": inc.rootCause or f"Incident severity {inc.severity}",
                "rootCause": inc.rootCause,
                "causalChain": inc.causalChain,
                "timeline": inc.postmortem.timeline if inc.postmortem else None,
                "proposedFix": next(
                    (a.actionType.value for a in inc.actions if a.status.value == "pending"), None
                ),
                "fixApplied": any(a.status.value == "executed" for a in inc.actions),
                "fixResult": next(
                    (a.notes for a in inc.actions if a.status.value == "executed"), None
                ),
                "postmortem": inc.postmortem.rootCauseAnalysis if inc.postmortem else None,
                "createdAt": inc.startedAt.isoformat(),
                "resolvedAt": inc.resolvedAt.isoformat() if inc.resolvedAt else None,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    try:
        inc = await db.incident.find_unique(
            where={"id": incident_id},
            include={"app": True, "actions": True, "postmortem": True},
        )
        if not inc:
            raise HTTPException(status_code=404, detail="Incident not found")
        return {
            "id": inc.id,
            "appId": inc.appId,
            "app": inc.app,
            "status": inc.status.value,
            "summary": inc.rootCause or f"Incident severity {inc.severity}",
            "rootCause": inc.rootCause,
            "causalChain": inc.causalChain,
            "timeline": inc.postmortem.timeline if inc.postmortem else None,
            "proposedFix": next(
                (a.actionType.value for a in inc.actions if a.status.value == "pending"), None
            ),
            "fixApplied": any(a.status.value == "executed" for a in inc.actions),
            "fixResult": next(
                (a.notes for a in inc.actions if a.status.value == "executed"), None
            ),
            "postmortem": inc.postmortem.rootCauseAnalysis if inc.postmortem else None,
            "createdAt": inc.startedAt.isoformat(),
            "resolvedAt": inc.resolvedAt.isoformat() if inc.resolvedAt else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))