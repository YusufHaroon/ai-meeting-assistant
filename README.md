# AI Meeting Assistant

A completely free, locally-running AI meeting assistant that captures your system audio (Teams, Zoom, etc.), transcribes speech using `faster-whisper`, and generates smart response suggestions using local `Ollama` models.

## Setup Instructions

### 1. Install System Audio Routing (Windows)
Since we want to capture "system audio" (what other people are saying) instead of just your microphone:
1. Download **VB-CABLE Virtual Audio Device** for free: https://vb-audio.com/Cable/
2. Extract the ZIP and run `VBCABLE_Setup_x64.exe` as Administrator.
3. Reboot your computer.
4. Open Windows Sound Settings.
5. Set your **Playback Device** to `CABLE Input`.
6. Set your meeting software (Teams/Zoom) output to the same `CABLE Input`.
*(Note: Windows WASAPI loopback is also supported automatically, but VB-CABLE is the most reliable fallback).*

### 2. Install Python Dependencies
Ensure you have Python 3.10+ installed.
```powershell
cd backend
pip install -r requirements.txt
```
*(Note: The first time you run this, it will automatically download a ~140MB `faster-whisper` model).*

### 3. Install and Run Ollama (Local LLM)
1. Download Ollama from https://ollama.com and install it.
2. Open a terminal and pull the Llama 3 model:
```powershell
ollama pull llama3
```
3. Keep Ollama running in the background (it starts automatically, or run `ollama serve`).

### 4. Run the Backend
Start the FastAPI server:
```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Open the Frontend
Since the frontend is pure HTML/JS, you don't need a heavy Node.js server.
Simply double-click:
```
frontend/index.html
```
Or open it via Live Server in VS Code, or python's http server:
```powershell
cd frontend
python -m http.server 3000
```
Then go to `http://localhost:3000` in your browser.

---

## How to Use
1. Ensure Ollama and the Backend are running.
2. Open the Website.
3. Click **"Start Assistant"**.
4. Join your meeting. The live transcript will appear on the left.
5. Whenever a **question** is asked OR a **pause** occurs in the conversation, the AI will generate:
   - 1 short response
   - 1 follow-up question
   - 1 opinion
...and display them instantly on the right!
