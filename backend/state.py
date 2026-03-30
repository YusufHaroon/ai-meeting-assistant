"""
state.py - Shared in-memory state for the AI Meeting Assistant.
All modules import from here to read/write shared state.
"""

from collections import deque
from threading import Lock

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
MAX_HISTORY_CHUNKS = 10  # Sliding window: keep last N transcribed chunks

# --------------------------------------------------------------------------
# Shared state (protected by a threading Lock)
# --------------------------------------------------------------------------
_lock = Lock()

_state = {
    "is_running": False,           # True while the audio loop is active
    "latest_transcript": "",       # Most recent transcribed text chunk
    "conversation_history": deque(maxlen=MAX_HISTORY_CHUNKS),  # All chunks
    "latest_ai_response": None,    # Latest dict from the LLM (or None)
    "status": "idle",              # "idle" | "listening" | "processing" | "error"
    "error_message": "",           # Human-readable error if status == "error"
}


# --------------------------------------------------------------------------
# Public helpers (thread-safe)
# --------------------------------------------------------------------------

def get_snapshot() -> dict:
    """Return a JSON-serialisable copy of current state."""
    with _lock:
        return {
            "is_running": _state["is_running"],
            "latest_transcript": _state["latest_transcript"],
            "conversation_history": list(_state["conversation_history"]),
            "latest_ai_response": _state["latest_ai_response"],
            "status": _state["status"],
            "error_message": _state["error_message"],
        }


def set_running(value: bool) -> None:
    with _lock:
        _state["is_running"] = value
        _state["status"] = "listening" if value else "idle"


def append_transcript(text: str) -> None:
    """Add a new transcribed chunk to history and update latest."""
    text = text.strip()
    if not text:
        return
    with _lock:
        _state["latest_transcript"] = text
        _state["conversation_history"].append(text)


def set_ai_response(response: dict) -> None:
    """Store the latest structured LLM output."""
    with _lock:
        _state["latest_ai_response"] = response


def set_status(status: str, error_message: str = "") -> None:
    with _lock:
        _state["status"] = status
        _state["error_message"] = error_message


def is_running() -> bool:
    with _lock:
        return _state["is_running"]


def get_history_text() -> str:
    """Return conversation history joined as a single string for LLM prompting."""
    with _lock:
        return "\n".join(_state["conversation_history"])
