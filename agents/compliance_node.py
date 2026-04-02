from __future__ import annotations

import asyncio
import json
from typing import Any, Dict
import os
from openai import AsyncOpenAI

from core.state import ComplianceReport, PermitState


def _build_compliance_prompt(state: PermitState) -> str:
    """Prompt for the primary compliance agent."""

    specs = state.get("extracted_specs")
    laws = state.get("relevant_laws", [])

    return (
        "You are a senior municipal building code reviewer.\n"
        "Decide compliance based ONLY on:\n"
        f"- Extracted specs: {specs!r}\n"
        f"- Retrieved zoning snippets (with SOURCE_LINK):\n{json.dumps(laws, indent=2)}\n\n"
        "You MUST respond with ONLY a valid JSON object (no markdown, no extra text) in this exact format:\n"
        "{\n"
        '  "status": "PASS" | "FAIL" | "WARNING",\n'
        '  "reasoning": "short explanation",\n'
        '  "citations": [{"law_excerpt": "quote", "source_link": "link"}]\n'
        "}\n\n"
        "Respond with ONLY the JSON object, nothing else."
    )


def _build_critic_prompt(proposal_json: str, state: PermitState) -> str:
    """Prompt for the Auditor (critic) to challenge the initial proposal."""

    laws = state.get("relevant_laws", [])
    return (
        "You are the Auditor for a municipal building code review.\n"
        "You must be adversarial and search for errors, missing citations, or contradictions.\n\n"
        f"Initial assessment JSON:\n{proposal_json}\n\n"
        f"Relevant zoning snippets (with SOURCE_LINK):\n{json.dumps(laws, indent=2)}\n\n"
        "If materially incorrect, output a corrected JSON object in the SAME shape.\n"
        "If substantially correct, repeat the original JSON.\n"
        "You MUST respond with ONLY a valid JSON object (no markdown, no extra text).\n"
        "Respond with ONLY the JSON object, nothing else."
    )


async def _call_claude(prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
    """Call OpenAI GPT-4o and parse JSON."""

    client = AsyncOpenAI()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=25,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError("OpenAI request timed out") from exc

    # OpenAI returns the response in response.choices[0].message.content
    content_text = response.choices[0].message.content
    if not content_text:
        raise ValueError("Empty response from GPT-4o")

    # Strip markdown code blocks if present
    content_text = content_text.strip()
    if content_text.startswith("```json"):
        content_text = content_text[7:]
    if content_text.startswith("```"):
        content_text = content_text[3:]
    if content_text.endswith("```"):
        content_text = content_text[:-3]
    content_text = content_text.strip()
    return json.loads(content_text)


def _bump_token_usage(state: PermitState, node: str, prompt: int, completion: int) -> None:
    """Accumulate token usage for observability."""

    usage = state.get("token_usage") or {}
    node_usage = usage.get(node, {})
    node_usage["prompt_tokens"] = node_usage.get("prompt_tokens", 0) + prompt
    node_usage["completion_tokens"] = node_usage.get("completion_tokens", 0) + completion
    usage[node] = node_usage
    state["token_usage"] = usage


async def compliance_node(state: PermitState) -> PermitState:
    """
    Compliance node implementing a Critic pattern (Proposer + Auditor).
    """

    # If OpenAI is not configured, degrade gracefully with a WARNING.
    if not os.getenv("OPENAI_API_KEY"):
        state["compliance_report"] = {
            "status": "WARNING",
            "reasoning": (
                "Compliance agent is not configured (missing OPENAI_API_KEY). "
                "Blueprint specs and relevant laws were computed, but no final "
                "LLM-based compliance judgment was generated."
            ),
            "citations": [],
        }
        return state

    try:
        # Proposer
        proposer_prompt = _build_compliance_prompt(state)
        proposer = await _call_claude(proposer_prompt)
        # Auditor
        critic_prompt = _build_critic_prompt(json.dumps(proposer), state)
        auditor = await _call_claude(critic_prompt)
    except Exception as exc:  # pragma: no cover
        error_msg = f"compliance_node: LLM failed: {exc!r}"
        state["errors"] = (state.get("errors") or []) + [error_msg]

        # Fallback deterministic report if OpenAI is unavailable or times out
        state["compliance_report"] = {
            "status": "WARNING",
            "reasoning": "OpenAI compliance evaluation failed; using fallback heuristic.",
            "citations": [],
        }

        # Add simple heuristic-based violation detection from extracted specs.
        specs = state.get("extracted_specs") or {}
        rules = []
        try:
            if specs.get("height", 0) > 50:
                rules.append("Height exceeds 50m, possible non-compliance.")
            if specs.get("setbacks", {}).get("front", 0) < 20:
                rules.append("Front setback below 20ft, possible non-compliance.")
            if not specs.get("fire_safety_exists"):
                rules.append("Missing required fire safety features.")
        except Exception:
            pass

        if rules:
            state["compliance_report"]["reasoning"] += " " + " ".join(rules)

        return state

    report: ComplianceReport = {
        "status": auditor.get("status", "WARNING"),
        "reasoning": auditor.get("reasoning", "Assessment incomplete; defaulted to WARNING."),
        "citations": auditor.get("citations", []),
    }
    state["compliance_report"] = report
    return state

