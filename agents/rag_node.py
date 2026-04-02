from __future__ import annotations

from typing import List

from qdrant_client import QdrantClient

from core.state import ExtractedSpecs, PermitState
from services.vector_store import EmbeddingClient, QdrantHybridVectorStore, ZoningLawDocument


class OpenAIEmbeddingClient:
    """Minimal async embedding adapter for hybrid retrieval."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self._model = model

    async def embed(self, text: str) -> list[float]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        response = await client.embeddings.create(model=self._model, input=text)
        return list(response.data[0].embedding)


def _build_specs_query(specs: ExtractedSpecs) -> str:
    """Convert `ExtractedSpecs` into a retrieval query for zoning codes."""

    setbacks = specs.setbacks or {}
    parts: List[str] = [
        f"zoning rules for building of approximately {specs.sq_ft:.0f} square feet",
        f"maximum height around {specs.height:.1f} feet",
        "setback requirements",
    ]
    for key in ("front", "rear", "left", "right"):
        if setbacks.get(key) is not None:
            parts.append(f"{key} setback about {setbacks.get(key)} feet")
    if specs.fire_safety_exists:
        parts.append("fire safety, sprinklers, emergency egress requirements")
    return ", ".join(parts)


def _default_vector_store() -> QdrantHybridVectorStore:
    """Create a default QdrantHybridVectorStore using env vars."""

    import os

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "zoning_codes")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    embedding_client: EmbeddingClient = OpenAIEmbeddingClient()

    return QdrantHybridVectorStore(
        client=client,
        collection_name=collection_name,
        embedding_client=embedding_client,
        text_field="text",
        source_link_field="source_link",
    )


def _bump_token_usage(state: PermitState, node: str, prompt: int, completion: int) -> None:
    """Accumulate token usage for observability."""

    usage = state.get("token_usage") or {}
    node_usage = usage.get(node, {})
    node_usage["prompt_tokens"] = node_usage.get("prompt_tokens", 0) + prompt
    node_usage["completion_tokens"] = node_usage.get("completion_tokens", 0) + completion
    usage[node] = node_usage
    state["token_usage"] = usage


async def rag_node(state: PermitState) -> PermitState:
    """
    Retrieve relevant zoning laws using hybrid (dense + keyword/BM25-style) search.

    Writes `state['relevant_laws']` as strings that include `SOURCE_LINK:` for XAI.
    """

    specs = state.get("extracted_specs")
    if specs is None:
        state["errors"] = (state.get("errors") or []) + ["rag_node: extracted_specs missing."]
        return state

    store = _default_vector_store()
    query = _build_specs_query(specs)

    try:
        docs: List[ZoningLawDocument] = await store.hybrid_search(query=query, limit=8)
    except Exception as exc:  # pragma: no cover
        state["errors"] = (state.get("errors") or []) + [f"rag_node: retrieval failed: {exc!r}"]
        return state

    state["relevant_laws"] = [f"{d.text}\n\nSOURCE_LINK: {d.source_link}" for d in docs]
    return state

