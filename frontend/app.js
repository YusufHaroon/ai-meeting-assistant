/**
 * app.js - Frontend logic for the AI Meeting Assistant.
 * Handles API endpoints, state polling, and DOM updates.
 */

const API_BASE = "http://localhost:8000";

// DOM Elements
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusIndicator = document.getElementById("status-indicator");
const transcriptStatus = document.getElementById("transcript-status");
const aiStatus = document.getElementById("ai-status");
const transcriptBox = document.getElementById("transcript-box");
const suggestionsBox = document.getElementById("suggestions-box");

// State
let pollInterval = null;
let processedChunks = new Set();
let lastAiResponseString = null;
let isRunning = false;

// Initial setup
btnStart.addEventListener("click", startAssistant);
btnStop.addEventListener("click", stopAssistant);

// --- API Calls ---

async function startAssistant() {
    try {
        btnStart.disabled = true;
        btnStart.innerText = "Starting...";
        
        const res = await fetch(`${API_BASE}/start`, { method: "POST" });
        if (!res.ok && res.status !== 409) throw new Error("Failed to start backend");
        
        isRunning = true;
        updateUIState();
        
        // Start polling immediately
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(pollBackend, 2000);
        
    } catch (err) {
        console.error(err);
        alert("Error starting backend. Is the FastAPI server running on port 8000?");
        btnStart.disabled = false;
        btnStart.innerText = "Start Assistant";
    }
}

async function stopAssistant() {
    try {
        btnStop.disabled = true;
        btnStop.innerText = "Stopping...";
        
        const res = await fetch(`${API_BASE}/stop`, { method: "POST" });
        if (!res.ok && res.status !== 409) throw new Error("Failed to stop backend");
        
        isRunning = false;
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        updateUIState();
        
    } catch (err) {
        console.error(err);
        btnStop.disabled = false;
        btnStop.innerText = "Stop";
    }
}

async function pollBackend() {
    try {
        const res = await fetch(`${API_BASE}/latest`);
        if (!res.ok) throw new Error("Poll failed");
        
        const data = await res.json();
        
        // Update general status
        if (data.is_running !== isRunning) {
            isRunning = data.is_running;
            updateUIState();
            if (!isRunning) {
                clearInterval(pollInterval);
                return;
            }
        }
        
        updateIndicators(data.status, data.error_message);
        
        // To avoid missing transcript chunks if they arrive fast, 
        // we'll aggressively fetch /history to render everything.
        await fetchHistory();
        
        // Handle AI response
        if (data.latest_ai_response) {
            const aiRespJson = JSON.stringify(data.latest_ai_response);
            if (aiRespJson !== lastAiResponseString) {
                lastAiResponseString = aiRespJson;
                renderAiSuggestion(data.latest_ai_response);
            }
        }
        
    } catch (err) {
        console.error("Polling error:", err);
        aiStatus.innerText = "Server Disconnected";
        aiStatus.style.color = "var(--accent-red)";
    }
}

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/history`);
        if (!res.ok) return;
        const data = await res.json();
        const historyArray = data.conversation_history;
        
        // Render only new chunks based on index
        historyArray.forEach((text, index) => {
            const chunkId = `chunk-${index}`;
            if (!processedChunks.has(chunkId)) {
                renderTranscriptObj(text);
                processedChunks.add(chunkId);
            }
        });
    } catch (err) {
        console.error(err);
    }
}

// --- DOM Rendering ---

function updateUIState() {
    if (isRunning) {
        btnStart.style.display = "none";
        btnStop.style.display = "block";
        btnStop.disabled = false;
        btnStop.innerText = "Stop";
        statusIndicator.classList.add("active");
        
        if (transcriptBox.innerHTML.includes("placeholder")) {
            transcriptBox.innerHTML = "";
        }
    } else {
        btnStart.style.display = "block";
        btnStart.disabled = false;
        btnStart.innerText = "Start Assistant";
        btnStop.style.display = "none";
        statusIndicator.classList.remove("active");
        
        transcriptStatus.innerText = "Stopped";
        aiStatus.innerText = "Stopped";
    }
}

function updateIndicators(status, errorMsg) {
    if (status === "error") {
        transcriptStatus.innerText = "Error";
        aiStatus.innerText = "Error";
        aiStatus.style.color = "var(--accent-red)";
        console.error("Backend Error:", errorMsg);
        return;
    }
    
    aiStatus.style.color = ""; // reset
    if (status === "listening") {
        transcriptStatus.innerText = "Listening...";
        aiStatus.innerText = "Waiting for cues...";
    } else if (status === "processing") {
        transcriptStatus.innerText = "Transcribing...";
        aiStatus.innerText = "Thinking...";
        aiStatus.style.color = "var(--status-processing)";
    }
}

function renderTranscriptObj(text) {
    const div = document.createElement("div");
    div.className = "transcript-chunk";
    div.textContent = text;
    transcriptBox.appendChild(div);
    
    // Auto scroll
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
}

function renderAiSuggestion(response) {
    if (suggestionsBox.innerHTML.includes("placeholder")) {
        suggestionsBox.innerHTML = "";
    }
    
    const div = document.createElement("div");
    div.className = "ai-suggestion-card";
    
    if (response.error) {
        div.innerHTML = `<p class="error-text">⚠️ ${response.text}</p>`;
    } else {
        // Wrap text in PRE to respect newlines from LLM
        div.innerHTML = `<pre>${response.text}</pre>`;
    }
    
    // Prepend to show newest at the top
    suggestionsBox.insertBefore(div, suggestionsBox.firstChild);
}
