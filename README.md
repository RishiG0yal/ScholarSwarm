# ScholarSwarm

**Multi-Agent AI Research Paper Briefing Engine**

🌐 **Live Demo:** https://scholarswarm.vercel.app

Upload a PDF or PPTX and get a fully verified research brief in minutes — with claims cross-checked against the source, figures described by vision AI, and an interactive context map connecting every element of the paper.

---

## Features

### Core Pipeline
- **3-Agent AI System** — Extractor → Critic → Simplifier running in sequence
- **Full Paper Reading** — reads all pages, splits into chunks, processes in parallel
- **Claim Verification** — every extracted claim is verified against the source text with a confidence score and exact quote
- **ELI5 Mode** — toggle between academic summary and plain-English explanation with a real-world analogy
- **Readability Score** — Flesch-Kincaid reading level and score

### Document Parsing
- PDF and PPTX support
- Layout-aware text extraction (handles two-column papers)
- Table extraction with garbage filtering
- Figure/chart analysis via Gemini Vision
- Equation extraction (regex + Gemini Vision)
- Citation pattern extraction (20+ formats)

### Visualization
- **Context Map** — force-directed graph connecting claims, key terms, and limitations
- **Citation Network** — D3 graph of related papers from Semantic Scholar
- **PDF Viewer** — in-browser PDF viewer with page jump and source quote highlighting

### Research Tools
- **Ask the Paper** — BM25-powered RAG Q&A using llama-3.3-70b or groq/compound
- **Compare Papers** — side-by-side analysis of two papers with conflict detection
- **Similar Papers** — Semantic Scholar integration with citation counts
- **Flashcards** — 3D flip study cards generated from the paper
- **Export** — Markdown download, Notion clipboard copy, AI audio brief (Gemini TTS)
- **Share Brief** — shareable URL for any analyzed paper

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.12+ |
| Extraction | Groq llama-3.1-8b-instant (chunks) + llama-3.3-70b-versatile (merge) |
| Verification | Groq llama-3.3-70b-versatile (critic) |
| Simplification | groq/compound-mini → llama-3.3-70b fallback |
| Q&A | groq/compound → llama-3.3-70b fallback |
| Vision | Gemini 2.0 Flash (figures + equations) |
| Text-to-Speech | Gemini 2.5 Flash TTS |
| PDF parsing | PyMuPDF + pdfplumber |
| PPTX parsing | python-pptx |
| RAG retrieval | BM25 (pure Python, no vector DB) |
| Deployment | Vercel (frontend) + Render (backend) |

---

## Local Setup

### 1. Clone and create structure

```bash
git clone https://github.com/yourname/scholarswarm
cd scholarswarm
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:5173

---

## Environment Variables

### Backend `.env`

```
GROQ_API_KEY=gsk_...          # Required - https://console.groq.com
GEMINI_API_KEY=AIza...         # Required - https://aistudio.google.com
FRONTEND_URL=https://your-app.vercel.app   # For production CORS
```

### Frontend `.env.local`

```
VITE_API_URL=http://localhost:8000   # Local
# or
VITE_API_URL=https://your-api.onrender.com   # Production
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload PDF/PPTX - runs full 3-agent pipeline |
| `GET` | `/brief/{id}` | Retrieve cached brief by share ID |
| `GET` | `/pdf/{id}` | Serve uploaded PDF for in-browser viewer |
| `POST` | `/ask` | BM25 RAG Q&A against the paper |
| `POST` | `/tts` | Gemini TTS - returns audio/wav |
| `GET` | `/similar?title=` | Find related papers via Semantic Scholar |
| `GET` | `/health` | Health check (used for Render warm-up ping) |

---

## Deploy

### Render (Backend)

1. New Web Service → connect repo
2. Root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variables: `GROQ_API_KEY`, `GEMINI_API_KEY`, `FRONTEND_URL`

### Vercel (Frontend)

1. New Project → import repo
2. Root directory: `frontend`
3. Framework preset: Vite
4. Environment variable: `VITE_API_URL=https://your-api.onrender.com`

### After deploy

Update `FRONTEND_URL` in Render to `https://scholarswarm.vercel.app`, then redeploy backend.

**Live URLs:**
- Frontend: https://scholarswarm.vercel.app
- Backend: https://scholarswarm.onrender.com

---

## Architecture

```
Browser
  │
  ├── Vercel (React + Vite)
  │     ├── Upload PDF/PPTX
  │     ├── Context Map (react-force-graph-2d)
  │     ├── Citation Graph (D3)
  │     ├── PDF Viewer (react-pdf)
  │     └── Compare Mode
  │
  └── Render (FastAPI)
        │
        ├── POST /upload
        │     ├── PyMuPDF — text extraction (all pages)
        │     ├── pdfplumber — table extraction
        │     ├── Gemini Vision — figure analysis
        │     ├── Parallel chunks → Groq 8b (extractor)
        │     ├── Groq 70b (merge)
        │     ├── Parallel claims → Groq 8b/70b (critic)
        │     └── Groq compound-mini (simplifier)
        │
        ├── POST /ask — BM25 retrieval → Groq compound
        ├── POST /tts — Gemini TTS
        └── GET /similar — Semantic Scholar
```

---

## Rate Limits (Free Tiers)

| Service | Free Limit |
|---|---|
| Groq | 14,400 req/day, 6,000 TPM per model |
| Gemini | 1,500 req/day (Flash) |
| Semantic Scholar | ~100 req/min |

Processing a 14-page paper uses approximately 20-30 Groq requests.

---

## Project by SR CODEx
