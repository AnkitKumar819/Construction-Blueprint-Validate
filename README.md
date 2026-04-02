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

### Project Structure

```
construction-blueprint-validate/
├── agents/                    # LangGraph-based agentic nodes
│   ├── orchestrator.py       # Main agent orchestration logic
│   ├── vision_node.py        # GPT-4o Vision blueprint parsing
│   ├── rag_node.py           # Claude-based compliance reasoning
│   └── compliance_node.py    # Zoning & safety rule validation
├── api/                      # FastAPI server
│   └── main.py              # REST API endpoints
├── core/                     # Core application logic
│   └── state.py             # State management for agents
├── services/                 # Business logic services
│   └── vector_store.py      # Qdrant integration
├── scripts/                  # Utility scripts
│   └── ingest_city_codes.py # Data ingestion
├── frontend/                 # Web UI (HTML/CSS/JS)
├── data/                     # Sample zoning codes
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

### Architecture

The system uses a multi-agent architecture powered by **LangGraph**:

1. **Vision Node** - Extracts blueprint elements using GPT-4o Vision
2. **RAG Node** - Retrieves relevant zoning codes from Qdrant vector DB
3. **Compliance Node** - Evaluates blueprint against regulations
4. **Orchestrator** - Coordinates agent execution and state management

### Key Technologies

- **LLMs**: OpenAI GPT-4o (vision), Anthropic Claude 3.5 Sonnet (reasoning)
- **Vector DB**: Qdrant (hybrid search with BM25 + semantic similarity)
- **Framework**: FastAPI for REST API, LangGraph for agent orchestration
- **Frontend**: Vanilla HTML/CSS/JavaScript

### API Endpoints

#### POST `/validate`
Validates a blueprint image against zoning regulations.

**Request**: Multipart form-data with image file
**Response**: JSON with compliance status and violations

```bash
curl -X POST \
  -F "file=@blueprint.jpg" \
  http://localhost:8000/validate
```

### Environment Setup

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required keys:
- `OPENAI_API_KEY` - From [OpenAI](https://platform.openai.com/api-keys)
- `ANTHROPIC_API_KEY` - From [Anthropic](https://console.anthropic.com/)
- `QDRANT_URL` - Qdrant instance URL (local or cloud)
- `QDRANT_API_KEY` - API key if using Qdrant Cloud

### Development

Install development dependencies:

```bash
pip install -r requirements.txt
```

Run health checks:

```bash
python health_check.py
```

Test the API:

```bash
python test_api.py
```

### Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit changes: `git commit -am 'Add my feature'`
3. Push to branch: `git push origin feature/my-feature`
4. Open a Pull Request

### License

This project is licensed under the MIT License - see the LICENSE file for details (if present).
