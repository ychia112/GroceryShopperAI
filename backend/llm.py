import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8001/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "tinyllama-1.1b-chat-v1.0.Q4_K_M")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

async def chat_completion(messages, temperature: float = 0.2, max_tokens: int = 512) -> str:
    """
    Calls an OpenAI-compatible /v1/chat/completions endpoint (e.g., llama.cpp or vLLM).
    """
    url = f"{LLM_API_BASE}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
