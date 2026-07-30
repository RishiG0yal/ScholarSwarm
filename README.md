# ScholarSwarm

Multi-Agent AI Research Paper Briefing Engine. Upload a PDF or PPTX and get a verified brief with claims, limitations, flashcards, tables, figures, and more.

## Stack

- **Frontend**: React + Vite + Tailwind CSS → Vercel
- **Backend**: FastAPI + Python → Render
- **LLM**: Groq (llama3-8b-8192) — 3 agents: Extractor, Critic, Simplifier
- **Vision**: Gemini 1.5 Flash for figure analysis
- **Parsing**: PyMuPDF + pdfplumber + python-pptx

## Setup

### Backend

```bash
cd backend
cp .env.example .env
# Fill in GROQ_API_KEY and GEMINI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000
npm run dev
```

## Deploy

### Render (Backend)
- Root: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env: `GROQ_API_KEY`, `GEMINI_API_KEY`, `FRONTEND_URL`

### Vercel (Frontend)
- Root: `frontend`
- Framework: Vite
- Env: `VITE_API_URL=https://your-app.onrender.com`

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload PDF/PPTX, returns full analysis |
| GET | `/brief/{id}` | Retrieve cached brief by ID |
| POST | `/ask` | Ask a question about the paper |
| GET | `/similar?title=` | Find similar papers via Semantic Scholar |
| GET | `/health` | Health check |
