# DocuMind-AI: Full-Stack RAG for Intelligent Document QA

![Cover Image](./assets/cover.png)

---

## 🚀 Quick Start

### Prerequisites
- Node.js (v16+)
- Python 3.8+
- OpenAI API Key

---

## ⚙️ Installation & Setup

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env` inside `backend/`:

```env
OPENAI_API_KEY=your_api_key_here

# Models
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4.1-mini

# RAG settings
CHUNK_SIZE=500
RETRIEVAL_TOP_K=3
MAX_HISTORY_TURNS=10

# Storage
STORAGE_BASE=storage

# Retrieval & Reranking
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
BM25_WEIGHT=0.3
FAISS_WEIGHT=0.7
MAX_CONTEXT_TOKENS=2000
RERANK_TOP_N=5
```

Start backend server:

```bash
uvicorn main:app --reload --port 8000
```

---

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

27 tests across chunking, embedding, retrieval, reranking, query classification, and context compression.

---

## 📁 Project Structure

```
DocuMind-AI/
├── backend/
│   ├── main.py
│   ├── core/
│   │   ├── config.py               # Centralized config via .env
│   │   ├── logger.py               # Structured JSON logger
│   │   └── metrics.py              # In-process latency & token metrics
│   ├── routes/
│   │   └── upload.py               # API endpoints
│   ├── services/
│   │   ├── chunking.py             # Page-aware text chunking
│   │   ├── embedding.py            # Batch embeddings with retry
│   │   ├── retrieval.py            # Hybrid BM25 + FAISS search
│   │   ├── reranking.py            # CrossEncoder reranking
│   │   ├── query_classifier.py     # Query type detection
│   │   ├── context.py              # Token budget + compression
│   │   ├── generation.py           # LLM answer + citations
│   │   ├── rag.py                  # Compatibility shim
│   │   ├── pdf.py                  # Multi-format text extraction
│   │   └── llm.py                  # OpenAI client helpers
│   ├── tests/
│   │   ├── test_chunking.py
│   │   ├── test_embedding.py
│   │   ├── test_retrieval.py
│   │   ├── test_reranking.py
│   │   ├── test_query_classifier.py
│   │   └── test_context.py
│   ├── storage/                    # FAISS indexes + chunk JSON
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── App.jsx
    │   └── index.css
    ├── package.json
    └── vite.config.js
```

---

## 🏗️ System Architecture

![RAG Pipeline](./assets/rag-pipeline.svg)

### Pipeline

1. User uploads a document
2. Text extracted and split into page-aware chunks (`chunking.py`)
3. Chunks embedded in batches with retry logic (`embedding.py`)
4. Embeddings stored in a per-document FAISS index (`retrieval.py`)
5. On question, query is embedded and retrieved via **hybrid BM25 + FAISS search**
6. Retrieved chunks are **reranked** by a CrossEncoder model (`reranking.py`)
7. Query is **classified** (factual / summary / comparison) to select the right prompt (`query_classifier.py`)
8. Context is **compressed** to fit within token budget (`context.py`)
9. GPT-4.1-mini generates the answer with inline citations (`generation.py`)
10. Latency and token usage are **logged and tracked** per request (`logger.py`, `metrics.py`)

---

## ✨ Features

- 📄 Multi-format upload — PDF, DOCX, PPTX, TXT
- 🤖 RAG-based AI Q&A grounded in your documents
- 🔍 Hybrid retrieval — BM25 keyword + FAISS semantic search
- 🧠 CrossEncoder reranking for higher answer quality
- 🎯 Query classification — tailored prompts per question type
- 🧾 Context compression — token-efficient chunk selection
- 📚 Multi-document support
- 🔖 Source citations with page number and snippet
- 💬 Chat history export (Markdown / JSON / TXT)
- 🧠 Conversation memory (session-based)
- 🗂️ Document management — list, rename, delete
- 📊 Observability — structured JSON logs, latency tracking, token usage per request
- 🎨 Modern UI with Framer Motion animations
- 📱 Fully responsive
- ⚡ Batch embeddings with exponential backoff
- ⚙️ Config-driven via `.env`

---

## 📊 Observability

Every request is logged as a structured JSON line to stdout:

```json
{"ts":"2026-05-10T10:22:01Z","level":"INFO","logger":"upload","msg":"ask_request","query_type":"factual","total_latency_ms":1423.5,"prompt_tokens":812,"completion_tokens":190}
```

A live metrics summary is available at:

```
GET http://localhost:8000/metrics
```

Example response:

```json
{
  "total_requests": 12,
  "latency_ms": { "avg": 1312.4, "min": 980.1, "max": 1823.6 },
  "tokens": {
    "prompt_total": 9744,
    "completion_total": 2280,
    "prompt_avg": 812.0,
    "completion_avg": 190.0
  }
}
```

Token usage and latency are also displayed inline in the chat UI beneath each answer.

---

## 🛠️ Tech Stack

**Frontend:** React 18, Vite, Framer Motion, Lucide Icons

**Backend:** FastAPI, OpenAI GPT-4.1-mini, FAISS, BM25, sentence-transformers, pypdf, python-docx, python-pptx

**Testing:** pytest

---

## 📂 Supported File Types

| Format | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Word | `.docx`, `.doc` |
| PowerPoint | `.pptx`, `.ppt` |
| Text | `.txt`, `.md` |

---

## 📝 License

MIT License — free to use and modify.
