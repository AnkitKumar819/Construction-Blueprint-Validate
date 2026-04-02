## Permit-to-Build Agentic Orchestrator

This project validates construction blueprints against municipal zoning and safety regulations using an agentic workflow:

- FastAPI backend (`api/`)
- LangGraph orchestrator and agents (`agents/`)
- GPT-4o Vision for multimodal blueprint parsing
- Claude 3.5 Sonnet for legal RAG and compliance reasoning
- Qdrant for hybrid (dense + keyword/BM25-style) retrieval of zoning codes

### Quick Start

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure environment**

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-key-or-empty-if-not-needed
QDRANT_COLLECTION=zoning_codes
```

3. **Ingest city codes into Qdrant**

```bash
python scripts/ingest_city_codes.py
```

4. **Run the API**

```bash
uvicorn api.main:app --reload
```

Then POST a multipart file to `/validate` with a blueprint image (or a pre-rendered page from a PDF).

### City Code Ingestion Notes

The ingestion script expects `data/zoning_code.txt.txt` and upserts chunks into Qdrant with at minimum:

- `text`: the code excerpt
- `source_link`: a canonical link for explainability (XAI)

For real deployments, replace the simple section-based chunker with a semantic chunker and use real, stable `source_link` values (e.g., the city code portal URL).
