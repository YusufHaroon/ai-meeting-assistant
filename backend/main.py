"""
main.py - FastAPI backend for the AI Meeting Assistant.

Endpoints
---------
GET  /          → health check
POST /start     → starts the background audio+AI processing loop
POST /stop      → stops the loop
GET  /latest    → returns latest transcript + AI response (polled by frontend)
GET  /history   → returns full conversation history

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import state
import audio_listener
from faster_whisper import WhisperModel
import llm
# --------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------
app = FastAPI(title="AI Meeting Assistant", version="1.0.0")

# Allow the plain HTML/JS frontend (served from file:// or a dev server) to
# call this API without CORS errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background worker thread (set in /start, cleared in /stop)
_worker_thread: threading.Thread | None = None
_whisper_model: WhisperModel | None = None


# --------------------------------------------------------------------------
# Background processing loop (placeholder — Steps 2-4 will fill this in)
# --------------------------------------------------------------------------
def _processing_loop() -> None:
    """
    Main loop:
      1. Capture audio chunks        (Step 2 ✅)
      2. Transcribe via Whisper      (Step 3 — placeholder)
      3. Generate AI suggestions     (Step 4 — placeholder)
    """
    global _whisper_model
    if _whisper_model is None:
        state.set_status("processing", "Loading Whisper model...")
        print("[worker] Loading Whisper model (base.en) on CPU...")
        _whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")
        print("[worker] Whisper model loaded.")

    state.set_status("listening")
    print("[worker] Processing loop started.")

    try:
        audio_listener.start_capture()
        last_was_speech = False

        for chunk in audio_listener.capture_chunks():
            if not state.is_running():
                break

            # ── Step 3: transcribe chunk ──────────────────────────────────
            # beam_size=1 is fast; language="en" skips auto-detection overhead
            segments, _ = _whisper_model.transcribe(chunk, beam_size=1, language="en")
            text = " ".join([seg.text for seg in segments]).strip()

            if text:
                print(f"[worker] Transcribed: {text}")
                state.append_transcript(text)

                # ── Step 4: generate AI response (Question condition) ─────
                if "?" in text:
                    print("[worker] Question detected! Generating AI response...")
                    state.set_status("processing", "Generating AI suggestion (Question)...")
                    resp = llm.generate_suggestions(state.get_history_text(), text)
                    state.set_ai_response(resp)
                    state.set_status("listening")
                
                last_was_speech = True
            else:
                # ── Step 4: generate AI response (Pause/silence condition)
                if last_was_speech:
                    print("[worker] Pause detected! Generating AI response...")
                    state.set_status("processing", "Generating AI suggestion (Pause)...")
                    history = state.get_history_text()
                    latest = state.get_snapshot()["latest_transcript"]
                    if history:
                        resp = llm.generate_suggestions(history, latest)
                        state.set_ai_response(resp)
                    state.set_status("listening")
                else:
                    print("[worker] (Silence)")
                
                last_was_speech = False

    except Exception as exc:
        print(f"[worker] Error: {exc}")
        state.set_status("error", str(exc))
    finally:
        audio_listener.stop_capture()
        state.set_status("idle")
        print("[worker] Processing loop stopped.")


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    return {"message": "AI Meeting Assistant API is running.", "status": state.get_snapshot()["status"]}


@app.post("/start", summary="Start the audio processing loop")
def start():
    global _worker_thread

    if state.is_running():
        raise HTTPException(status_code=409, detail="Already running.")

    state.set_running(True)

    _worker_thread = threading.Thread(target=_processing_loop, daemon=True, name="meeting-worker")
    _worker_thread.start()

    return {"message": "Meeting assistant started.", "status": "listening"}


@app.post("/stop", summary="Stop the audio processing loop")
def stop():
    if not state.is_running():
        raise HTTPException(status_code=409, detail="Not currently running.")

    state.set_running(False)

    # Give the worker thread up to 5 s to finish its current iteration
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)

    return {"message": "Meeting assistant stopped.", "status": "idle"}


@app.get("/latest", summary="Poll for the latest transcript and AI response")
def latest():
    """
    Called by the frontend every ~2 seconds.
    Returns the most recent transcribed chunk and the latest AI suggestion.
    """
    snap = state.get_snapshot()
    return JSONResponse({
        "status": snap["status"],
        "latest_transcript": snap["latest_transcript"],
        "latest_ai_response": snap["latest_ai_response"],
        "is_running": snap["is_running"],
        "error_message": snap["error_message"],
    })


@app.get("/history", summary="Return the full conversation history window")
def history():
    snap = state.get_snapshot()
    return JSONResponse({
        "conversation_history": snap["conversation_history"],
        "chunk_count": len(snap["conversation_history"]),
    })
