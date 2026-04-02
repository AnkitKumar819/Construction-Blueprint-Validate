from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, StateGraph

from agents.compliance_node import compliance_node
from agents.rag_node import rag_node
from agents.vision_node import vision_node
from core.state import PermitState


def build_permit_graph() -> StateGraph:
    """
    Build the LangGraph DAG for the Permit-to-Build orchestrator.

    DAG: Start -> VisionNode -> RAGNode -> ComplianceNode -> End
    """

    graph = StateGraph(PermitState)
    graph.add_node("vision", vision_node)
    graph.add_node("rag", rag_node)
    graph.add_node("compliance", compliance_node)

    graph.set_entry_point("vision")
    graph.add_edge("vision", "rag")
    graph.add_edge("rag", "compliance")
    graph.add_edge("compliance", END)
    return graph


def compile_permit_app() -> Callable[[PermitState], Any]:
    """Compile the graph into an app exposing async `ainvoke`."""

    return build_permit_graph().compile()

