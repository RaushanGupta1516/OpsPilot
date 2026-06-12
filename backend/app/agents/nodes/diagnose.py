from app.agents.state import IncidentState
from app.rag.ingestor import search_failure_patterns
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional
import json


# structured output schema for LLM response
class DiagnosisOutput(BaseModel):
    severity: int                  # 1-5
    root_cause: str
    confidence: float              # 0.0-1.0
    recommended_action: str        # restart_service, notify_only, escalate, rollback_deploy
    explanation: str


async def diagnose_node(state: IncidentState) -> IncidentState:
    """
    retrieves relevant failure patterns from qdrant RAG,
    then calls gemini to diagnose the incident.
    falls back to groq if gemini fails.
    """
    print(f"[diagnose] diagnosing incident for {state['app_name']}")

    # build query for RAG from trigger metric + causal chain
    query = _build_rag_query(state)
    rag_results = await search_failure_patterns(query, top_k=3)

    print(f"[diagnose] retrieved {len(rag_results)} RAG patterns")

    # try gemini first, fall back to groq
    diagnosis = await _call_llm_with_fallback(state, rag_results)

    print(f"[diagnose] severity={diagnosis.severity} confidence={diagnosis.confidence} action={diagnosis.recommended_action}")

    return {
        **state,
        "severity": diagnosis.severity,
        "root_cause": diagnosis.root_cause,
        "confidence": diagnosis.confidence,
        "recommended_action": diagnosis.recommended_action,
        "rag_patterns": rag_results,
    }


def _build_rag_query(state: IncidentState) -> str:
    trigger = state["trigger_metric"]
    parts = []

    if trigger.get("response_time_ms") and trigger["response_time_ms"] > 2000:
        parts.append(f"high response time {trigger['response_time_ms']}ms")

    if trigger.get("error_rate") and trigger["error_rate"] > 0:
        parts.append("error rate elevated")

    if not trigger.get("is_healthy"):
        parts.append("service unhealthy connection failed")

    parts.extend(state.get("causal_chain", []))
    return " ".join(parts) if parts else "service degradation anomaly detected"


async def _call_llm_with_fallback(state: IncidentState, rag_results: list) -> DiagnosisOutput:
    prompt = _build_prompt(state, rag_results)

    # try gemini first
    try:
        return await _call_gemini(prompt)
    except Exception as e:
        print(f"[diagnose] gemini failed: {e}, trying groq...")

    # groq fallback
    try:
        return await _call_groq(prompt)
    except Exception as e:
        print(f"[diagnose] groq failed: {e}, using rule-based fallback")

    # rule-based fallback - no LLM
    return _rule_based_diagnosis(state)


async def _call_gemini(prompt: str) -> DiagnosisOutput:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
    )

    structured_llm = llm.with_structured_output(DiagnosisOutput)
    result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    return result


async def _call_groq(prompt: str) -> DiagnosisOutput:
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=settings.groq_api_key,
        temperature=0.1,
    )

    structured_llm = llm.with_structured_output(DiagnosisOutput)
    result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    return result


def _build_prompt(state: IncidentState, rag_results: list) -> str:
    trigger = state["trigger_metric"]
    causal_chain = "\n".join(f"- {c}" for c in state.get("causal_chain", []))
    rag_context = ""

    for r in rag_results:
        p = r.get("pattern", {})
        rag_context += f"\nPattern: {p.get('symptom', '')}\nRoot cause: {p.get('root_cause', '')}\nFix: {', '.join(p.get('fix_steps', []))}\n"

    return f"""You are an expert DevOps engineer analyzing a production incident.

App: {state['app_name']}
Environment: {state['app_environment']}
URL: {state['app_url']}

Current metrics:
- Response time: {trigger.get('response_time_ms')}ms
- Status code: {trigger.get('status_code')}
- Error rate: {trigger.get('error_rate')}
- Healthy: {trigger.get('is_healthy')}

Timeline of events:
{causal_chain}

Relevant failure patterns from knowledge base:
{rag_context}

Based on this information, diagnose the incident and provide:
1. Severity (1=minor, 5=critical)
2. Root cause (be specific)
3. Confidence score (0.0-1.0)
4. Recommended action (one of: restart_service, notify_only, escalate, rollback_deploy)
5. Brief explanation

Be concise and specific. Focus on actionable diagnosis."""


def _rule_based_diagnosis(state: IncidentState) -> DiagnosisOutput:
    trigger = state["trigger_metric"]
    rt = trigger.get("response_time_ms", 0) or 0
    er = trigger.get("error_rate", 0) or 0
    healthy = trigger.get("is_healthy", True)

    if not healthy:
        return DiagnosisOutput(
            severity=5,
            root_cause="Service is completely unreachable",
            confidence=0.9,
            recommended_action="restart_service",
            explanation="Service not responding to health checks"
        )
    elif rt > 5000:
        return DiagnosisOutput(
            severity=4,
            root_cause="Severe response time degradation",
            confidence=0.7,
            recommended_action="notify_only",
            explanation=f"Response time {rt}ms is critically high"
        )
    elif er > 0.1:
        return DiagnosisOutput(
            severity=3,
            root_cause="Elevated error rate detected",
            confidence=0.7,
            recommended_action="notify_only",
            explanation=f"Error rate at {er * 100:.1f}%"
        )
    else:
        return DiagnosisOutput(
            severity=2,
            root_cause="Minor performance degradation",
            confidence=0.6,
            recommended_action="notify_only",
            explanation="Metrics slightly outside normal range"
        )