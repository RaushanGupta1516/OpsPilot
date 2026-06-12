
import json

from app.agents.state import IncidentState
from app.core.database import db
from langgraph.types import interrupt
from datetime import datetime, timezone




async def action_node(state: IncidentState) -> IncidentState:
    """
    decides what action to take based on severity and environment.
    production + severity >= 4: human-in-the-loop via interrupt()
    staging: auto-execute
    severity < 4: notify only
    """
    print(f"[action] severity={state['severity']} env={state['app_environment']}")



    # create incident record first
    incident = await db.incident.create(
        data={
            "app": {"connect": {"id": state["app_id"]}},
            "severity": state["severity"],
            "rootCause": state["root_cause"],
            "causalChain": json.dumps(state["causal_chain"]),
            "confidence": state["confidence"],
            "fingerprint": f"{state['app_id']}_{state['root_cause'][:50]}",
        }
    )



    recommended = state["recommended_action"]
    severity = state["severity"]
    environment = state["app_environment"]

    # low severity - just log and notify
    if severity <= 2:
        await db.action.create(
            data={
                "incidentId": incident.id,
                "actionType": "notify_only",
                "status": "executed",
                "executedAt": datetime.now(timezone.utc),
                "executedBy": "auto",
                "notes": f"Low severity ({severity}/5) — logged only",
            }
        )
        print(f"[action] low severity — notify only")
        return {
            **state,
            "incident_id": incident.id,
            "action_taken": "notify_only",
            "action_status": "executed",
            "human_approved": None,
            "should_act": False,
        }

    # medium severity - notify, no action
    if severity == 3:
        await db.action.create(
            data={
                "incidentId": incident.id,
                "actionType": "notify_only",
                "status": "executed",
                "executedAt": datetime.now(timezone.utc),
                "executedBy": "auto",
                "notes": f"Severity 3 — developer notified, no auto-action taken",
            }
        )
        print(f"[action] severity 3 — notifying developer")
        return {
            **state,
            "incident_id": incident.id,
            "action_taken": "notify_only",
            "action_status": "executed",
            "human_approved": None,
            "should_act": False,
        }

    # high severity (4-5) on production — human-in-the-loop
    if severity >= 4 and environment == "production":
        print(f"[action] high severity production incident — requesting human approval")

        # create pending action record
        action = await db.action.create(
            data={
                "incidentId": incident.id,
                "actionType": recommended,
                "status": "pending",
                "notes": f"Awaiting human approval. Root cause: {state['root_cause']}",
            }
        )

        # interrupt() pauses graph execution here
        # the frontend will show approve/reject UI
        # Command(resume=...) will continue execution
        approval = interrupt({
            "incident_id": incident.id,
            "action_id": action.id,
            "app_name": state["app_name"],
            "root_cause": state["root_cause"],
            "recommended_action": recommended,
            "severity": severity,
            "confidence": state["confidence"],
            "message": f"OpsPilot wants to {recommended} on {state['app_name']}. Approve?",
        })

        human_approved = approval.get("approved", False)

        if human_approved:
            print(f"[action] approved — executing {recommended}")
            await db.action.update(
                where={"id": action.id},
                data={
                    "status": "executed",
                    "decidedAt": datetime.now(timezone.utc),
                    "executedAt": datetime.now(timezone.utc),
                    "executedBy": "human",
                }
            )
            action_status = "executed"
        else:
            print(f"[action] rejected by developer")
            await db.action.update(
                where={"id": action.id},
                data={
                    "status": "rejected",
                    "decidedAt": datetime.now(timezone.utc),
                    "executedBy": "human",
                }
            )
            action_status = "rejected"

        return {
            **state,
            "incident_id": incident.id,
            "action_taken": recommended,
            "action_status": action_status,
            "human_approved": human_approved,
            "should_act": False,
        }

    # high severity on staging — auto execute
    print(f"[action] staging env — auto executing {recommended}")
    await db.action.create(
        data={
            "incidentId": incident.id,
            "actionType": recommended,
            "status": "executed",
            "executedAt": datetime.now(timezone.utc),
            "executedBy": "auto",
            "notes": "Auto-executed on staging environment",
        }
    )

    return {
        **state,
        "incident_id": incident.id,
        "action_taken": recommended,
        "action_status": "executed",
        "human_approved": None,
        "should_act": False,
    }