# ScholarSwarm

An AI-powered research paper analyzer that extracts claims, fact-checks them against the source text, and generates study aids (briefs, flashcards, concept maps) with exact page-level citations.

## Features

- **No Hallucinations:** Every claim presented to the user is verified against the original text by a dedicated fact-checker agent.
- **Page-Level Traceability:** Click on any claim, flashcard, or concept map node to jump directly to the exact page and sentence in the embedded PDF viewer.
- **Smart Ingestion:** Handles multi-column academic layouts, detects tables/figures, and falls back to OCR for scanned PDFs.
- **Premium UI:** A dynamic, responsive dark-mode interface built with glassmorphism and micro-animations.

## Prerequisites

- Python 3.10+ (Tested on 3.13)
- Google Gemini API Key (Free tier works perfectly)
- [Optional] Tesseract OCR for scanned PDF support

## Installation

1. Clone the repository
2. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables:
   - Copy `.env.example` to `.env`
   - Add your `GEMINI_API_KEY` (Get one from [Google AI Studio](https://aistudio.google.com/))

## Running the Application

1. Start the FastAPI backend from the `backend` directory:
   ```bash
   python main.py
   ```
2. Open your browser and navigate to `http://localhost:8000`

## Architecture

- **Frontend:** Vanilla HTML/CSS/JS served directly by FastAPI (no Node.js build step required). Features D3.js for concept maps and PDF.js for the document viewer.
- **Backend:** FastAPI orchestrating a 7-stage pipeline:
  1. PDF Ingestion (PyMuPDF / Tesseract)
  2. Semantic Chunking
  3. Embeddings (sentence-transformers + ChromaDB)
  4. Extractor Agent (Gemini 2.5 Flash)
  5. Fact-Checker Agent (Gemini 2.5 Flash)
  6. Citation Formatting
  7. Output Generation (Brief, Flashcards, Concept Map)

## Privacy & Data Handling

ScholarSwarm respects your data. Uploaded PDFs and generated vectors are stored locally and are automatically cleaned up when your session expires (30 minutes of inactivity) or when you explicitly start a new analysis. No data is stored long-term.
