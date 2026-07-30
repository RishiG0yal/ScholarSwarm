"""
PaperVerify — Configuration and constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from the backend folder or the workspace root.
for env_path in [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    BASE_DIR / ".env.local",
    BASE_DIR.parent / ".env.local",
]:
    if env_path.exists():
        load_dotenv(env_path, override=False)
        break

# Fallback: load from the current working directory if present.
load_dotenv(override=False)
TEMP_DIR = BASE_DIR / "temp"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Create directories
for d in [TEMP_DIR, CACHE_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Server ─────────────────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# ── PDF Constraints ───────────────────────────────────────────────────
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PAGES = 100

# ── Chunking ──────────────────────────────────────────────────────────
CHUNK_MIN_WORDS = 300
CHUNK_MAX_WORDS = 500
SHORT_PAPER_THRESHOLD = 5  # pages

# ── Agent Settings ────────────────────────────────────────────────────
AGENT_TIMEOUT_SECONDS = 30
AGENT_MAX_RETRIES = 1
REJECTION_RATE_THRESHOLD = 0.30  # 30% unsupported → low quality warning
CHUNK_BATCH_SIZE = 6  # chunks per extractor call

# ── Session ───────────────────────────────────────────────────────────
SESSION_IDLE_TIMEOUT_MINUTES = 30
SESSION_CLEANUP_INTERVAL_MINUTES = 5

# ── Citation ──────────────────────────────────────────────────────────
MAX_QUOTE_WORDS = 15
