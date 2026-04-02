from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels


class EmbeddingClient(Protocol):
    """Protocol for async embedding backends."""

    async def embed(self, text: str) -> Sequence[float]:
        """Return a vector embedding for the given text."""


@dataclass
class ZoningLawDocument:
    """Normalized zoning-law snippet with required `source_link` metadata."""

    id: str
    text: str
    source_link: str
    score: float
    metadata: Dict[str, Any]


class QdrantHybridVectorStore:
    """
    Hybrid (dense + keyword/BM25-style) search over zoning codes backed by Qdrant.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        embedding_client: EmbeddingClient,
        text_field: str = "text",
        source_link_field: str = "source_link",
        keyword_weight: float = 0.4,
        dense_weight: float = 0.6,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._embedding_client = embedding_client
        self._text_field = text_field
        self._source_link_field = source_link_field
        self._keyword_weight = keyword_weight
        self._dense_weight = dense_weight

    async def _dense_search(self, query: str, limit: int) -> List[ZoningLawDocument]:
        vector = await self._embedding_client.embed(query)
        result = self._client.query_points(
            collection_name=self._collection_name,
            query=list(vector),
            limit=limit,
        )

        docs: List[ZoningLawDocument] = []
        for point in result.points:
            payload = point.payload or {}
            docs.append(
                ZoningLawDocument(
                    id=str(point.id),
                    text=str(payload.get(self._text_field, "")),
                    source_link=str(payload.get(self._source_link_field, "")),
                    score=float(point.score or 0.0),
                    metadata=dict(payload),
                )
            )
        return docs

    def _keyword_search(self, query: str, limit: int) -> List[ZoningLawDocument]:
        """
        Keyword/BM25-style match using Qdrant text indexing on `text_field`.

        Note: `scroll` does not return scores; we treat hits as uniform.
        """

        points, _ = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key=self._text_field,
                        match=qmodels.MatchText(text=query),
                    )
                ]
            ),
            limit=limit,
        )

        docs: List[ZoningLawDocument] = []
        for point in points:
            payload = point.payload or {}
            docs.append(
                ZoningLawDocument(
                    id=str(point.id),
                    text=str(payload.get(self._text_field, "")),
                    source_link=str(payload.get(self._source_link_field, "")),
                    score=1.0,
                    metadata=dict(payload),
                )
            )
        return docs

    async def hybrid_search(self, query: str, limit: int = 10) -> List[ZoningLawDocument]:
        """Run dense + keyword search and merge results with weighted scoring."""

        dense = await self._dense_search(query, limit=limit)
        keyword = self._keyword_search(query, limit=limit)

        combined: Dict[str, ZoningLawDocument] = {}

        def add(docs: List[ZoningLawDocument], weight: float) -> None:
            for d in docs:
                if d.id not in combined:
                    combined[d.id] = ZoningLawDocument(
                        id=d.id,
                        text=d.text,
                        source_link=d.source_link,
                        score=d.score * weight,
                        metadata=dict(d.metadata),
                    )
                else:
                    combined[d.id].score += d.score * weight

        add(dense, self._dense_weight)
        add(keyword, self._keyword_weight)

        ranked = sorted(combined.values(), key=lambda d: d.score, reverse=True)
        return ranked[:limit]

