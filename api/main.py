from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from agents.orchestrator import compile_permit_app
from core.state import PermitState


load_dotenv()

logger = logging.getLogger("permit_to_build")
logging.basicConfig(level=logging.INFO)


app = FastAPI(title="Permit-to-Build Orchestrator", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


permit_app = compile_permit_app()


# Serve static frontend files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Serve the frontend index page."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found"}


@app.get("/styles.css")
async def serve_css():
    """Serve CSS file."""
    css_path = os.path.join(frontend_path, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return {"error": "CSS file not found"}


@app.get("/dashboard")
async def serve_dashboard():
    """Serve the system testing dashboard."""
    dashboard_path = os.path.join(frontend_path, "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}


@app.middleware("http")
async def token_usage_logging_middleware(request: Request, call_next):
    """
    Basic logging middleware to track token usage per node.

    Each orchestrator run can populate `state['token_usage']` with a dictionary
    mapping node name -> token count. The final state is logged here once the
    request has completed.
    """

    response = await call_next(request)

    state: PermitState | None = getattr(request.state, "permit_state", None)
    if state is not None:
        token_usage = state.get("token_usage") or {}
        logger.info("Token usage per node: %s", token_usage)

    return response


@app.post("/validate")
async def validate_permit(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    """
    Validate a construction blueprint against zoning laws.

    Accepts a multipart file upload (image/PDF). For PDFs, a separate OCR pipeline
    should convert a representative page to an image before calling the vision node.
    """

    raw_bytes = await file.read()
    raw_b64 = base64.b64encode(raw_bytes).decode("utf-8")

    initial_state: PermitState = {
        "raw_blueprint": raw_b64,
        "errors": [],
    }

    final_state: PermitState = await permit_app.ainvoke(initial_state)
    request.state.permit_state = final_state

    report = final_state.get("compliance_report")
    clarification_needed = (
        report.get("status") == "CLARIFICATION_NEEDED" if isinstance(report, dict) else False
    )

    extracted_specs = final_state.get("extracted_specs", {})
    if hasattr(extracted_specs, "model_dump"):
        extracted_specs = extracted_specs.model_dump()

    response_payload: Dict[str, Any] = {
        "compliance_report": report,
        "extracted_specs": extracted_specs,
        "relevant_laws": final_state.get("relevant_laws", []),
        "clarification_needed": clarification_needed,
        "errors": final_state.get("errors", []),
    }

    return JSONResponse(content=response_payload)

