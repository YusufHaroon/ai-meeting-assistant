"""
audio_listener.py - System audio capture for the AI Meeting Assistant.

How it works
------------
1. Lists all available audio devices and picks the best "loopback" / WASAPI
   device automatically (or uses the index you set in DEVICE_INDEX).
2. Records audio in overlapping chunks (CHUNK_DURATION seconds).
3. Each chunk is converted to mono float32 and placed on a thread-safe queue.
4. The background worker in main.py drains that queue for transcription.

Virtual Audio Cable setup (Windows)
------------------------------------
Install VB-CABLE (free): https://vb-audio.com/Cable/
• Set "CABLE Output" as the Windows default playback device  ← Teams audio goes here
• Select "CABLE Output" as the capture device below           ← we read from here

Alternatively, use WASAPI loopback (no extra software needed on Windows 10/11):
• Run `python audio_listener.py --list` to see device numbers.
• Set DEVICE_INDEX to the index of your speakers/headphones (loopback).
"""

import argparse
import queue
import threading
import time
from typing import Generator

import numpy as np
import sounddevice as sd

# --------------------------------------------------------------------------
# Configuration (override via env or edit directly)
# --------------------------------------------------------------------------
SAMPLE_RATE      = 16_000   # Hz — Whisper expects 16 kHz
CHUNK_DURATION   = 5        # seconds per chunk sent to Whisper
CHANNELS         = 1        # mono
DTYPE            = "float32"
DEVICE_INDEX     = None     # None = auto-select; set to int to pin a device

# --------------------------------------------------------------------------
# Shared queue — filled by audio callback, drained by the worker thread
# --------------------------------------------------------------------------
audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

# --------------------------------------------------------------------------
# Internal state
# --------------------------------------------------------------------------
_stop_event = threading.Event()
_stream: sd.InputStream | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def list_devices() -> None:
    """Print all audio devices so the user can identify the right one."""
    print("\nAvailable audio devices:")
    print("-" * 60)
    for i, dev in enumerate(sd.query_devices()):
        io = []
        if dev["max_input_channels"] > 0:
            io.append("IN")
        if dev["max_output_channels"] > 0:
            io.append("OUT")
        tag = ", ".join(io)
        print(f"  [{i:2d}] {dev['name']}  ({tag})  "
              f"SR={int(dev['default_samplerate'])} Hz")
    print("-" * 60)
    print("Set DEVICE_INDEX in audio_listener.py to the loopback/CABLE device.\n")


def _pick_device() -> int | None:
    """
    Auto-select a WASAPI loopback device on Windows, or fall back to default.
    Returns None to let sounddevice use its own default.
    """
    if DEVICE_INDEX is not None:
        return DEVICE_INDEX

    devices = sd.query_devices()
    # Prefer VB-CABLE or WASAPI loopback by keyword search
    keywords = ["cable output", "loopback", "stereo mix", "what u hear"]
    for i, dev in enumerate(devices):
        name = dev["name"].lower()
        if dev["max_input_channels"] > 0 and any(k in name for k in keywords):
            print(f"[audio] Auto-selected device [{i}]: {dev['name']}")
            return i

    print("[audio] No loopback device found — using system default input.")
    print("[audio] Run `python audio_listener.py --list` for device list.")
    return None  # sounddevice default


# --------------------------------------------------------------------------
# Core capture logic
# --------------------------------------------------------------------------

def _audio_callback(indata: np.ndarray, frames: int,
                    time_info, status) -> None:
    """Called by sounddevice for every audio block."""
    if status:
        print(f"[audio] Status: {status}")
    # Copy to avoid buffer reuse issues; squeeze to 1-D
    audio_queue.put(indata[:, 0].copy())


def _accumulate_chunks() -> Generator[np.ndarray, None, None]:
    """
    Yield one CHUNK_DURATION-second numpy array at a time by draining
    the queue and stitching blocks together.
    """
    samples_needed = int(SAMPLE_RATE * CHUNK_DURATION)
    buffer = np.array([], dtype=DTYPE)

    while not _stop_event.is_set():
        try:
            block = audio_queue.get(timeout=0.5)
            buffer = np.concatenate([buffer, block])
        except queue.Empty:
            continue

        if len(buffer) >= samples_needed:
            chunk = buffer[:samples_needed]
            buffer = buffer[samples_needed:]   # keep the remainder
            yield chunk


def start_capture() -> None:
    """
    Open the audio stream and start filling audio_queue.
    Call this from the background worker thread in main.py.
    Run capture_chunks() after this to get chunk iterables.
    """
    global _stream
    _stop_event.clear()
    device = _pick_device()

    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        device=device,
        callback=_audio_callback,
        blocksize=int(SAMPLE_RATE * 0.1),   # 100 ms blocks
    )
    _stream.start()
    print(f"[audio] Stream started — device={device}, "
          f"SR={SAMPLE_RATE} Hz, chunk={CHUNK_DURATION}s")


def stop_capture() -> None:
    """Signal the capture loop to stop and close the stream."""
    _stop_event.set()
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
        print("[audio] Stream stopped.")


def capture_chunks() -> Generator[np.ndarray, None, None]:
    """
    Generator that yields one numpy float32 array per CHUNK_DURATION seconds.
    Intended to be called from the main processing loop:

        start_capture()
        for chunk in capture_chunks():
            text = whisper.transcribe(chunk)
    """
    yield from _accumulate_chunks()


# --------------------------------------------------------------------------
# Standalone test (run directly to verify audio capture works)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio capture test")
    parser.add_argument("--list", action="store_true", help="List audio devices")
    parser.add_argument("--test", action="store_true", help="Capture one chunk and print stats")
    args = parser.parse_args()

    if args.list:
        list_devices()

    elif args.test:
        print(f"[test] Capturing {CHUNK_DURATION}s chunk …")
        start_capture()
        for chunk in capture_chunks():
            print(f"[test] Chunk shape: {chunk.shape}, "
                  f"min={chunk.min():.4f}, max={chunk.max():.4f}, "
                  f"rms={float(np.sqrt(np.mean(chunk**2))):.4f}")
            break   # only capture one chunk for the test
        stop_capture()
        print("[test] Done.")

    else:
        parser.print_help()
