from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import IncidentState
from app.agents.nodes.correlate import correlate_node
from app.agents.nodes.diagnose import diagnose_node
from app.agents.nodes.action import action_node
from app.agents.nodes.postmortem import postmortem_node


def should_continue_after_correlate(state: IncidentState) -> str:
    """skip to end if duplicate incident"""
    if state.get("is_duplicate"):
        return "end"
    return "diagnose"


def should_continue_after_action(state: IncidentState) -> str:
    """always generate postmortem after action"""
    return "postmortem"


def build_graph():
    graph = StateGraph(IncidentState)

    # add nodes
    graph.add_node("correlate", correlate_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("action", action_node)
    graph.add_node("postmortem", postmortem_node)

    # entry point
    graph.set_entry_point("correlate")

    # edges
    graph.add_conditional_edges(
        "correlate",
        should_continue_after_correlate,
        {
            "diagnose": "diagnose",
            "end": END,
        }
    )

    graph.add_edge("diagnose", "action")

    graph.add_conditional_edges(
        "action",
        should_continue_after_action,
        {
            "postmortem": "postmortem",
        }
    )

    graph.add_edge("postmortem", END)

    # use in-memory checkpointer for now
    # TODO: switch to AsyncPostgresSaver in phase 7
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer, interrupt_before=["action"])


# single graph instance
opspilot_graph = build_graph()