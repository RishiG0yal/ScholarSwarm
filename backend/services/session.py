"""
PaperVerify — Session management and cleanup.
"""
import asyncio
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import TEMP_DIR, SESSION_IDLE_TIMEOUT_MINUTES, SESSION_CLEANUP_INTERVAL_MINUTES, LOGS_DIR
from models.schemas import ProcessingStatus
from utils.logging_util import logger


class SessionData:
    """Tracks state for a single processing session."""

    def __init__(self, session_id: str, filename: str):
        self.session_id = session_id
        self.filename = filename
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.status = ProcessingStatus(
            session_id=session_id,
            stage="uploading",
            progress_pct=0,
            message="Preparing upload...",
        )
        self.results = None  # Will hold AnalysisResults once complete
        self.pdf_path: Path | None = None
        self.chromadb_collection_name: str | None = None
        self.is_saved = False  # User explicitly chose to save

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def update_status(self, stage: str, progress_pct: int, message: str, error_detail: str | None = None):
        """Update the processing status."""
        self.status = ProcessingStatus(
            session_id=self.session_id,
            stage=stage,
            progress_pct=progress_pct,
            message=message,
            error_detail=error_detail,
        )
        self.touch()

    @property
    def is_idle(self) -> bool:
        """Check if session has been idle beyond the timeout."""
        elapsed = (datetime.now(timezone.utc) - self.last_activity).total_seconds()
        return elapsed > SESSION_IDLE_TIMEOUT_MINUTES * 60


class SessionManager:
    """Manages all active sessions with auto-cleanup."""

    def __init__(self):
        self._sessions: dict[str, SessionData] = {}
        self._cleanup_task: asyncio.Task | None = None

    def create_session(self, filename: str) -> SessionData:
        """Create a new session and return it."""
        session_id = uuid.uuid4().hex[:12]
        session = SessionData(session_id=session_id, filename=filename)
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id} for '{filename}'")
        return session

    def get_session(self, session_id: str) -> SessionData | None:
        """Get a session by ID, or None if not found."""
        session = self._sessions.get(session_id)
        if session:
            session.touch()
        return session

    def delete_session(self, session_id: str):
        """Delete a session and clean up its resources."""
        session = self._sessions.pop(session_id, None)
        if not session:
            return

        # Clean up PDF file
        if session.pdf_path and session.pdf_path.exists():
            try:
                session.pdf_path.unlink()
                logger.info(f"Deleted PDF: {session.pdf_path}")
            except OSError as e:
                logger.warning(f"Failed to delete PDF {session.pdf_path}: {e}")

        # Clean up session temp directory
        session_dir = TEMP_DIR / session_id
        if session_dir.exists():
            try:
                shutil.rmtree(session_dir)
                logger.info(f"Deleted session dir: {session_dir}")
            except OSError as e:
                logger.warning(f"Failed to delete session dir {session_dir}: {e}")

        # Clean up log file (optional — keep for debugging)
        # log_file = LOGS_DIR / f"verification_{session_id}.jsonl"
        # if log_file.exists():
        #     log_file.unlink()

        logger.info(f"Session deleted: {session_id}")

    async def _cleanup_loop(self):
        """Background loop that cleans up idle sessions."""
        while True:
            await asyncio.sleep(SESSION_CLEANUP_INTERVAL_MINUTES * 60)
            idle_sessions = [
                sid for sid, s in self._sessions.items()
                if s.is_idle and not s.is_saved
            ]
            for sid in idle_sessions:
                logger.info(f"Auto-cleaning idle session: {sid}")
                self.delete_session(sid)

            if idle_sessions:
                logger.info(f"Cleaned up {len(idle_sessions)} idle session(s)")

    def start_cleanup_task(self):
        """Start the background cleanup loop."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session cleanup task started")

    def stop_cleanup_task(self):
        """Stop the background cleanup loop."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None


# Global singleton
session_manager = SessionManager()
