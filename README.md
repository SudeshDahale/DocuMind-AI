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
CHAT_MODEL=gpt-4o-mini

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

The frontend will be available at `http://localhost:3000`

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
│   │   ├── errors.py               # Retry + fallback decorator
│   │   ├── logger.py               # Structured JSON logger
│   │   └── metrics.py              # In-process latency & token metrics
│   ├── routes/
│   │   └── upload.py               # API endpoints
│   ├── services/
│   │   ├── chunking.py             # Page-aware text chunking
│   │   ├── embedding.py            # Batch embeddings with retry + fallback
│   │   ├── retrieval.py            # Hybrid BM25 + FAISS search
│   │   ├── reranking.py            # CrossEncoder reranking with fallback
│   │   ├── query_classifier.py     # Query type detection with fallback
│   │   ├── context.py              # Token budget + compression
│   │   ├── generation.py           # LLM answer + citations with retry
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
│   │   ├── LandingPage.jsx     # Workspace creation landing
│   │   ├── Sidebar.jsx         # Workspace + document manager
│   │   ├── ChatPanel.jsx       # Streaming chat interface
│   │   ├── SourcesPanel.jsx    # Retrieved chunk viewer with highlighting
│   │   ├── ComparePanel.jsx    # Document comparison interface
│   │   ├── ExplainPanel.jsx    # Detailed explanations panel
│   │   ├── ReportPanel.jsx     # Report generation panel
│   │   ├── FeatureBar.jsx      # Feature selection toolbar
│   │   └── Background.jsx      # Animated background effects
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
└── vite.config.js
```
---

## 🏗️ System Architecture

![RAG Pipeline](./assets/rag-pipeline.svg)

### Pipeline

1. User creates a **workspace** and uploads one or more documents into it
2. Text extracted and split into page-aware chunks (`chunking.py`)
3. Chunks embedded in batches with retry + zero-vector fallback (`embedding.py`)
4. Embeddings stored in a per-document FAISS index (`retrieval.py`)
5. On question, query is embedded and retrieved via **hybrid BM25 + FAISS search** across all docs in the workspace
6. Retrieved chunks are **reranked** by a CrossEncoder model — falls back gracefully if model unavailable (`reranking.py`)
7. Query is **classified** (factual / summary / comparison) with retry and fallback to `factual` (`query_classifier.py`)
8. Context is **compressed** to fit within token budget (`context.py`)
9. GPT-4o-mini generates the answer with inline citations — retries up to 3× with a user-friendly fallback message (`generation.py`)
10. Latency and token usage are **logged and tracked** per request (`logger.py`, `metrics.py`)
11. Answer streams progressively to the UI; retrieved source chunks appear in the **Sources panel** with text highlighting

---

## ✨ Features

### Core RAG Features
- 📄 **Multi-format upload** — PDF, DOCX, PPTX, TXT
- 🤖 **RAG-based AI Q&A** — answers grounded in your documents
- 🔍 **Hybrid retrieval** — BM25 keyword + FAISS semantic search
- 🧠 **CrossEncoder reranking** — higher answer quality with reranking
- 🎯 **Query classification** — tailored prompts per question type
- 🧾 **Context compression** — token-efficient chunk selection
- 🔖 **Source citations** — with page numbers and snippets

### Workspace & Document Management
- 📂 **Workspace system** — organize documents into named collections
- 🧠 **Multi-doc reasoning** — query across all documents in a workspace simultaneously
- 🗂️ **Document management** — add, remove, and rename documents per workspace
- 📝 **Workspace renaming** — update workspace names on the fly
- 🗑️ **Workspace deletion** — remove workspaces and associated documents

### Advanced UI Features
- ⚡ **Streaming responses** — answers reveal progressively with typing effect
- 🔎 **Source highlighting** — click citations to highlight matching text in Sources panel
- 🎨 **Modern SaaS UI** — 3-panel layout with animated background effects
- 🌈 **Gradient design system** — polished interface with accent colors and smooth animations
- 📱 **Responsive design** — works across desktop and mobile devices

### AI-Powered Features
- 💬 **Chat history** — maintains conversation context per workspace
- 📊 **Document comparison** — compare content across multiple documents (UI ready)
- 🔍 **Detailed explanations** — get in-depth explanations (UI ready)
- 📄 **Report generation** — create comprehensive reports (UI ready)

### Developer Experience
- 🚨 **Robust error handling** — retries with exponential backoff, graceful fallbacks
- 📊 **Observability** — structured JSON logs, latency tracking, token usage
- 🧪 **Comprehensive testing** — 27 tests covering all core functionality
- ⚙️ **Config-driven** — centralized configuration via `.env`
- 🔄 **Real-time metrics** — `/metrics` endpoint for monitoring

---

## 🎨 UI Components

### Landing Page
- Gradient animated title with "DocuMind" branding
- Feature badges showcasing key capabilities
- Workspace creation form with smooth animations
- Animated background with gradient orbs and grid overlay

### Main Application
- **Sidebar**: Workspace switcher, document uploader, file manager
- **Chat Panel**: Streaming AI responses with source citations
- **Sources Panel**: Retrieved chunks with click-to-highlight functionality
- **Feature Bar**: Quick access to Compare, Explain, and Report features (expandable)

---

## 🚨 Error Handling

Failures are handled at every layer rather than crashing the request:

| Layer | Retry | Fallback |
|---|---|---|
| Embedding (single) | 3× exponential backoff | raises — hard failure |
| Embedding (batch) | 3× per batch | zero vectors — indexing continues |
| Reranking | — | returns chunks unranked |
| Query classification | 2× | defaults to `"factual"` |
| LLM call | 3× | returns a user-friendly sorry message |
| `/upload` route | — | 422 for bad content, 500 for infra errors |
| `/ask` route | — | clean 500 with message |

---

## 📊 Observability

Every request is logged as a structured JSON line to stdout:

```json
{"ts":"2026-05-12T10:22:01Z","level":"INFO","logger":"upload","msg":"ask_request","query_type":"factual","total_latency_ms":1423.5,"prompt_tokens":812,"completion_tokens":190}
```

A live metrics summary is available at:
GET http://localhost:8000/metrics

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

**Frontend:** 
- React 18
- Vite
- Framer Motion (animations)
- Lucide Icons
- Custom CSS with CSS variables

**Backend:** 
- FastAPI
- OpenAI GPT-4o-mini
- FAISS (vector search)
- BM25 (keyword search)
- sentence-transformers (reranking)
- pypdf, python-docx, python-pptx (document parsing)

**Testing:** 
- pytest

---

## 📂 Supported File Types

| Format | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Word | `.docx`, `.doc` |
| PowerPoint | `.pptx`, `.ppt` |
| Text | `.txt`, `.md` |

---
---

## 📝 License

MIT License — free to use and modify.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
