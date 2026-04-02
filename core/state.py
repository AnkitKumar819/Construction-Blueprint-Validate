from __future__ import annotations

from typing import List, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


class ExtractedSpecs(BaseModel):
    """Structured architectural specifications extracted from the blueprint."""

    sq_ft: float = Field(..., description="Total square footage of the project.")
    setbacks: dict = Field(
        ...,
        description=(
            "Setback distances from property lines, e.g. "
            "{'front': 10.0, 'rear': 15.0, 'left': 5.0, 'right': 5.0} (in feet)."
        ),
    )
    height: float = Field(..., description="Maximum building height in feet.")
    fire_safety_exists: bool = Field(
        ...,
        description="Whether fire safety systems (sprinklers, exits, etc.) are present in the blueprint.",
    )


ComplianceStatus = Literal["PASS", "FAIL", "WARNING", "CLARIFICATION_NEEDED"]


class ComplianceReport(TypedDict, total=False):
    """Machine-readable compliance assessment with citations."""

    status: ComplianceStatus
    reasoning: str
    citations: List[dict]


class PermitState(TypedDict, total=False):
    """
    Shared orchestrator state for the Permit-to-Build pipeline.

    This state object is passed between LangGraph nodes and tracks:
    - raw_blueprint: original blueprint payload as bytes or base64-encoded string.
    - extracted_specs: structured architectural specs from the vision node.
    - relevant_laws: legal text snippets retrieved by the RAG node.
    - compliance_report: final compliance assessment with citations.
    - errors: any error tracebacks encountered during processing.
    - token_usage: optional per-node token accounting for observability.
    """

    raw_blueprint: bytes | str
    extracted_specs: ExtractedSpecs
    relevant_laws: List[str]
    compliance_report: ComplianceReport
    errors: NotRequired[List[str]]
    token_usage: NotRequired[dict]

