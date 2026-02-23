# Comp-Check Bot 🤖⚖️

A **production-ready RAG (Retrieval-Augmented Generation) web application** for legal contract compliance analysis.

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + Vite |
| **Backend** | FastAPI (Python 3.11) |
| **Database** | Neon Postgres (Serverless) |
| **Vector DB** | Milvus Cloud (Zilliz) |
| **Embeddings** | BGE-M3 via HuggingFace InferenceClient |
| **LLM** | Groq (`openai/gpt-oss-20b`) |
| **Deployment** | Render (separate backend + frontend services) |

---

## Project Structure

```
comp-check-bot/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Pydantic settings (env vars)
│   │   ├── api/
│   │   │   └── routes.py              # POST /query, GET /health
│   │   ├── services/
│   │   │   ├── postgres_service.py    # Neon Postgres + retry logic
│   │   │   ├── milvus_service.py      # Zilliz vector search
│   │   │   ├── embedding_service.py   # BGE-M3 embedding
│   │   │   └── rag_pipeline.py        # Full RAG orchestration
│   │   ├── schemas/
│   │   │   ├── request.py             # QueryRequest
│   │   │   └── response.py            # QueryResponse, RetrievedChunk, StructuredRecord
│   │   └── models/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env                            # (never commit – local only)
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Root component + state
│   │   ├── api.js                     # Fetch wrapper (VITE_API_BASE_URL)
│   │   ├── index.css                  # Full design system (CSS custom properties)
│   │   ├── main.jsx                   # ReactDOM entry
│   │   └── components/
│   │       ├── AnswerCard.jsx          # Markdown answer + copy button
│   │       ├── ChunksSection.jsx       # Collapsible chunks + score color coding
│   │       ├── RecordsTable.jsx        # Postgres records table with score bar
│   │       ├── LoadingCard.jsx         # Animated progress indicator
│   │       └── ErrorCard.jsx          # Error display
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── .env
│   └── .env.example
├── render.yaml                         # Render deployment config (both services)
└── .gitignore
```

---

## System Flow

```
User Query
   │
   ├── 1. Extract structured filters (Groq LLM)
   │         ↓
   ├── 2. Query Neon Postgres → matching contract_ids
   │         ↓
   ├── 3. Embed query with BGE-M3 (HuggingFace)
   │         ↓
   ├── 4. Milvus vector search filtered by contract_ids
   │         ↓
   ├── 5. Fetch full contract rows from Postgres
   │         ↓
   ├── 6. Build context (structured + clauses)
   │         ↓
   └── 7. Generate answer with Groq → Return JSON
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node 18+
- All credentials in `backend/.env`

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Start dev server (loads backend/.env automatically)
uvicorn app.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api calls to localhost:8000)
npm run dev
```

Visit: http://localhost:5173

> **Note:** The Vite dev server is pre-configured to proxy all `/api` requests to `http://localhost:8000`, so no CORS issues in local development.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_USER_NEON` | ✅ | Neon Postgres username |
| `DB_PW_NEON` | ✅ | Neon Postgres password |
| `DB_NEON_HOST` | ✅ | Neon Postgres host (pooler endpoint) |
| `DB_NEON_NAME` | ✅ | Database name (usually `neondb`) |
| `MILVUS_URI` | ✅ | Zilliz Cloud cluster URI |
| `MILVUS_API_KEY` | ✅ | Zilliz API token |
| `MILVUS_COLLECTION` | ❌ | Collection name (default: `legal_policy_vectors`) |
| `HF_TOKEN` | ✅ | HuggingFace API token for BGE-M3 |
| `GROQ_API_KEY` | ✅ | Groq API key |
| `GROQ_MODEL` | ❌ | LLM model (default: `openai/gpt-oss-20b`) |
| `PORT` | ❌ | Server port (default: `8000`) |
| `ALLOWED_ORIGINS` | ❌ | CORS origins (default: `*`) |
| `TOP_K` | ❌ | Vector search top-k (default: `5`) |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | ❌ (prod: ✅) | Backend URL, e.g. `https://comp-check-bot-backend.onrender.com`. Leave empty for local dev (proxy handles it). |

---

## API Reference

### `POST /api/v1/query`

```json
// Request
{ "query": "Show the Pending EU contracts with risk scores" }

// Response
{
  "answer": "**1. Executive Summary** ...",
  "retrieved_chunks": [
    {
      "chunk_text": "...",
      "similarity_score": 0.87,
      "contract_id": 6,
      "contract_type": "NDA"
    }
  ],
  "structured_records": [
    {
      "contract_id": 6,
      "vendor_name": "Helix Enterprises",
      "contract_type": "NDA",
      "duration_months": 36,
      "compliance_score": 73,
      "audit_status": "Pending",
      "contract_date": "2023-06-18",
      "jurisdiction": "France",
      "policy_name": "Data Privacy Policy",
      "region": "EU"
    }
  ]
}
```

### `GET /api/v1/health`

```json
{ "status": "ok", "message": "Comp-Check Bot is running" }
```

---

## Deploying on Render

The `render.yaml` at the root of `comp-check-bot/` defines **two services**:
- `comp-check-bot-backend` – Python web service
- `comp-check-bot-frontend` – Static site

### Step 1: Push to GitHub
```bash
git add .
git commit -m "feat: initial comp-check-bot project"
git push
```

### Step 2: Create Render Services

1. Go to [render.com](https://render.com) → New → **Blueprint**
2. Connect your GitHub repo
3. Select `comp-check-bot/render.yaml` as the blueprint
4. Render will detect both services automatically

### Step 3: Set Backend Environment Variables

In the Render dashboard for `comp-check-bot-backend`, add all secrets:

```
DB_USER_NEON      = <your neon user>
DB_PW_NEON        = <your neon password>
DB_NEON_HOST      = <your neon host>
DB_NEON_NAME      = neondb
MILVUS_URI        = <your zilliz uri>
MILVUS_API_KEY    = <your zilliz token>
HF_TOKEN          = <your huggingface token>
GROQ_API_KEY      = <your groq key>
ALLOWED_ORIGINS   = https://comp-check-bot-frontend.onrender.com
TOP_K             = 5
```

### Step 4: Set Frontend Environment Variable

In the Render dashboard for `comp-check-bot-frontend`, add:

```
VITE_API_BASE_URL = https://comp-check-bot-backend.onrender.com
```

> **Important:** Set `ALLOWED_ORIGINS` in the backend to the exact URL of your frontend service (no trailing slash).

### Step 5: Deploy

Click **Deploy** on each service. Render will:
- Backend: `pip install -r requirements.txt` → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Frontend: `npm install && npm run build` → serves `dist/`

---

## Milvus Collection Schema

```python
fields = [
    FieldSchema(name="id",            dtype=DataType.INT64,         is_primary=True, auto_id=True),
    FieldSchema(name="contract_id",   dtype=DataType.INT64),
    FieldSchema(name="embedding",     dtype=DataType.FLOAT_VECTOR,  dim=1024),
    FieldSchema(name="contract_type", dtype=DataType.VARCHAR,        max_length=100),
    FieldSchema(name="text_chunk",    dtype=DataType.VARCHAR,        max_length=5000),
]
# Index: IVF_FLAT, metric=COSINE, nlist=128
```

---

## Similarity Score Color Coding

| Score Range | Color | Meaning |
|-------------|-------|---------|
| ≥ 0.85 | 🟢 Green | High relevance |
| 0.70 – 0.84 | 🟠 Orange | Medium relevance |
| < 0.70 | 🔴 Red | Low relevance |

---

## Example Queries

```
"Show summary about contract with TransContinental Corp"
"Which contracts in the EU region are currently in Pending status and what are their risk scores?"
"Show me the Data Privacy related contracts in France and summarize their compliance requirements."
"What are the service agreement terms with Asiatrade Logistics?"
```
