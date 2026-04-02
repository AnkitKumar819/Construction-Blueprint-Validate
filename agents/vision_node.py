from __future__ import annotations

import base64
import json
from typing import Any, Dict

from openai import AsyncOpenAI
from pydantic import ValidationError

from core.state import ComplianceReport, ExtractedSpecs, PermitState


async def _encode_image_to_base64(raw_blueprint: bytes | str) -> str:
    """
    Ensure the blueprint payload is base64-encoded for GPT-4o vision input.

    The orchestrator can provide either:
    - raw bytes of an image (PNG/JPEG), or
    - a base64-encoded string.
    """

    if isinstance(raw_blueprint, bytes):
        return base64.b64encode(raw_blueprint).decode("utf-8")

    return raw_blueprint


def _build_chain_of_density_prompt() -> str:
    """
    Build a Chain-of-Density style prompt to maximize accuracy of architectural specs.

    The model is instructed to iteratively refine estimates and emit strict JSON.
    """

    return (
        "You are an expert building code analyst.\n"
        "You are given a single architectural blueprint image. Your task is to extract "
        "high-accuracy, structured specifications.\n\n"
        "Use a Chain-of-Density style process:\n"
        "1) Start with a coarse estimate of sq_ft, setbacks, height, and fire safety.\n"
        "2) Iteratively refine by locating scale bars/dimensions and cross-checking.\n"
        "3) If critical info is missing (e.g. NO SCALE FOUND), set uncertainty flags.\n\n"
        "Output ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "sq_ft": <number>,\n'
        '  "setbacks": {"front": <number>, "rear": <number>, "left": <number>, "right": <number>},\n'
        '  "height": <number>,\n'
        '  "fire_safety_exists": <true_or_false>,\n'
        '  "notes": {"no_scale_found": <true_or_false>, "setbacks_uncertain": <true_or_false>, "height_uncertain": <true_or_false>}\n'
        "}\n"
    )


def _post_process_specs(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Strip auxiliary fields and keep only ExtractedSpecs keys."""

    allowed_keys = {"sq_ft", "setbacks", "height", "fire_safety_exists"}
    return {k: v for k, v in raw_payload.items() if k in allowed_keys}


def _maybe_mark_clarification_needed(state: PermitState, raw_payload: Dict[str, Any]) -> None:
    """
    If uncertainty flags are present, attach a CLARIFICATION_NEEDED compliance_report.
    """

    notes = raw_payload.get("notes") or {}
    needs_clarification = any(
        bool(notes.get(flag))
        for flag in ("no_scale_found", "setbacks_uncertain", "height_uncertain")
    )
    if not needs_clarification:
        return

    report: ComplianceReport = {
        "status": "CLARIFICATION_NEEDED",
        "reasoning": (
            "Blueprint has missing or ambiguous information (e.g. no scale bar, unclear "
            "property lines, or uncertain height). Human clarification is recommended."
        ),
        "citations": [],
    }
    state["compliance_report"] = report


def _bump_token_usage(state: PermitState, node: str, prompt: int, completion: int) -> None:
    """Accumulate token usage for observability."""

    usage = state.get("token_usage") or {}
    node_usage = usage.get(node, {})
    node_usage["prompt_tokens"] = node_usage.get("prompt_tokens", 0) + prompt
    node_usage["completion_tokens"] = node_usage.get("completion_tokens", 0) + completion
    usage[node] = node_usage
    state["token_usage"] = usage


async def vision_node(state: PermitState) -> PermitState:
    """
    Extract architectural specs from `raw_blueprint` via GPT-4o Vision.

    Returns updated `PermitState` with validated `extracted_specs`. If the model
    indicates missing/ambiguous info, sets `compliance_report.status` to
    `CLARIFICATION_NEEDED`.
    """

    raw_blueprint = state.get("raw_blueprint")
    if raw_blueprint is None:
        state["errors"] = (state.get("errors") or []) + ["vision_node: raw_blueprint missing."]
        return state

    try:
        client = AsyncOpenAI()
        b64_image = await _encode_image_to_base64(raw_blueprint)
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _build_chain_of_density_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                        },
                    ],
                }
            ],
            temperature=0.1,
        )
        if response.usage is not None:
            _bump_token_usage(
                state,
                node="vision",
                prompt=response.usage.prompt_tokens or 0,
                completion=response.usage.completion_tokens or 0,
            )

        content = response.choices[0].message.content or "{}"
        raw_payload: Dict[str, Any] = json.loads(content)
        normalized = _post_process_specs(raw_payload)
        state["extracted_specs"] = ExtractedSpecs.model_validate(normalized)
        _maybe_mark_clarification_needed(state, raw_payload)
        return state
    except (json.JSONDecodeError, KeyError, IndexError, ValidationError) as exc:
        state["errors"] = (state.get("errors") or []) + [f"vision_node: parse/validate failed: {exc!r}"]
        return state
    except Exception as exc:  # pragma: no cover
        state["errors"] = (state.get("errors") or []) + [f"vision_node: model call failed: {exc!r}"]
        return state

