from __future__ import annotations

import asyncio
import os
from typing import List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "zoning_code.txt.txt")


async def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[list[float]]:
    """Embed a batch of texts using the same embedding model as retrieval."""

    client = AsyncOpenAI()
    response = await client.embeddings.create(model=model, input=texts)
    return [list(item.embedding) for item in response.data]


def chunk_zoning_text(raw_text: str) -> list[dict]:
    """
    Simple rule-based chunker for the sample zoning text file.

    Splits on lines starting with "SECTION ".
    """

    sections: list[dict] = []
    current: dict | None = None

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("SECTION "):
            if current is not None:
                sections.append(current)
            current = {"id": line.replace(" ", "_"), "title": line, "text_lines": []}
            continue
        if current is not None:
            current["text_lines"].append(line)

    if current is not None:
        sections.append(current)

    base_url = "https://example-city.gov/codes/ai-metro/residential"
    records: list[dict] = []
    for sec in sections:
        text = sec["title"] + "\n" + "\n".join(sec["text_lines"])
        records.append(
            {
                "id": sec["id"],
                "text": text,
                "source_link": f"{base_url}#{sec['id']}",
                "metadata": {"section_title": sec["title"]},
            }
        )
    return records


async def main() -> None:
    """Ingest `data/zoning_code.txt.txt` into Qdrant with `source_link` payloads."""

    load_dotenv()

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "zoning_codes")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read()

    records = chunk_zoning_text(raw_text)
    embeddings = await embed_texts([r["text"] for r in records])

    points = []
    for idx, (rec, vec) in enumerate(zip(records, embeddings, strict=True), start=1):
        points.append(
            qmodels.PointStruct(
                id=idx,  # Qdrant requires integer or UUID IDs; store section id in payload
                vector=vec,
                payload={
                    "text": rec["text"],
                    "source_link": rec["source_link"],
                    "section_id": rec["id"],
                    **rec.get("metadata", {}),
                },
            )
        )

    client.upsert(collection_name=collection_name, points=points)


if __name__ == "__main__":
    asyncio.run(main())

