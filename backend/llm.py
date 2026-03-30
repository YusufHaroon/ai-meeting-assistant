"""
llm.py - Local LLM integration using Ollama for the AI Meeting Assistant.

Expects Ollama to be running locally on http://localhost:11434
Recommended models: llama3 or mistral
Run `ollama run llama3` in your terminal before starting the server.
"""

import httpx

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"   # Automatically used by the generate endpoint

PROMPT_TEMPLATE = """You are a real-time meeting assistant.
Based on the conversation below, suggest what the user should say next.

Conversation:
{history}

Latest:
{chunk}

Generate:
* 1 short response the user can say
* 1 follow-up question
* 1 opinion
"""

# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def generate_suggestions(history: str, latest: str) -> dict:
    """
    Calls the local Ollama API to generate meeting suggestions.
    Returns a dictionary suitable for storing in state.latest_ai_response.
    """
    prompt = PROMPT_TEMPLATE.format(history=history, chunk=latest)
    
    try:
        # We use a short timeout so the audio loop doesn't block forever
        # if Ollama is generating slowly or is offline.
        response = httpx.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 150  # Keep it short
                }
            },
            timeout=15.0
        )
        response.raise_for_status()
        
        result_text = response.json().get("response", "").strip()
        
        return {
            "text": result_text,
            "error": False
        }
        
    except httpx.ConnectError:
        err_msg = "Error: Could not connect to Ollama. Is it running on port 11434?"
        print(f"[llm] {err_msg}")
        return {"text": err_msg, "error": True}
        
    except httpx.ReadTimeout:
        err_msg = "Error: Ollama generation timed out (model too slow?)."
        print(f"[llm] {err_msg}")
        return {"text": err_msg, "error": True}
        
    except Exception as e:
        err_msg = f"Error generating suggestions: {e}"
        print(f"[llm] {err_msg}")
        return {"text": err_msg, "error": True}

