from typing import TypedDict, Optional, List, Any
from datetime import datetime


class IncidentState(TypedDict):
    # app info
    app_id: str
    app_name: str
    app_url: str
    app_environment: str

    # what triggered the agent
    trigger_metric: dict          # the metric that caused the anomaly
    anomaly_reason: str           # why it was flagged

    # correlate node output
    is_duplicate: bool
    existing_incident_id: Optional[str]
    causal_chain: List[str]
    recent_metrics: List[dict]

    # diagnose node output
    severity: int                 # 1-5
    root_cause: str
    confidence: float             # 0-1
    recommended_action: str
    rag_patterns: List[dict]      # patterns retrieved from qdrant

    # action node output
    action_taken: str
    action_status: str            # pending, approved, rejected, executed
    human_approved: Optional[bool]
    incident_id: Optional[str]

    # postmortem node output
    postmortem_generated: bool
    postmortem_id: Optional[str]

    # control flow
    should_act: bool
    is_resolved: bool
    error: Optional[str]