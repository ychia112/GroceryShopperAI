import os
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Supported models
AVAILABLE_MODELS = {
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "api_key": os.getenv("OPENAI_API_KEY", "").strip()
    },
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY", "").strip(),
        "model": os.getenv("GEMINI_MODEL", "gemini-pro")
    }
}

# Configure Gemini SDK if key provided
if AVAILABLE_MODELS["gemini"]["api_key"]:
    gemini_api_key = AVAILABLE_MODELS["gemini"]["api_key"]
    genai.configure(api_key=gemini_api_key)

# Default model
DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai").strip().lower()

async def chat_completion(messages, temperature: float = 0.2, max_tokens: int = 512, model_name: str = None) -> str:
    """
    Supports multiple models: openai, gemini
    """
    # 選擇模型（使用傳入的模型名稱，或使用預設）
    if model_name is None:
        model_name = DEFAULT_MODEL
    
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Model '{model_name}' not available. Choose from: {list(AVAILABLE_MODELS.keys())}")
    
    config = AVAILABLE_MODELS[model_name]
    provider = model_name

    if provider == "openai":
        # OpenAI API endpoint
        url = f"{config['api_base']}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        payload = {
            "model": config["model"],
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

    elif provider == "gemini":
        # Google Generative AI SDK (official)
        model = genai.GenerativeModel(config["model"])
        
        # Convert OpenAI-style messages to Gemini format
        # Gemini expects [{"role": "user"/"model", "parts": [{"text": "..."}]}]
        gemini_messages = []
        for m in messages:
            role = m.get("role", "user")
            content_text = m.get("content", "")
            # Convert role: "assistant" -> "model", others stay as "user"
            gemini_role = "model" if role == "assistant" else "user"
            gemini_messages.append({
                "role": gemini_role,
                "parts": [{"text": content_text}]
            })
        
        # Use generate_content with permissive settings
        response = model.generate_content(
            gemini_messages,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        # Handle blocked responses gracefully
        try:
            if response.text:
                return response.text
        except ValueError:
            pass
        
        # If response was blocked, check candidates
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                if len(candidate.content.parts) > 0:
                    return candidate.content.parts[0].text
        
        return "[Response was filtered by Gemini safety policies]"

    else:
        # If reached here, unsupported provider
        raise ValueError(f"Unsupported provider: {provider}")
