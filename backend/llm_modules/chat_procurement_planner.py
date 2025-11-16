import json
from typing import List, Dict, Any

from llm_modules.llm_utils import (extract_goal, extract_json, format_chat_history,)
from llm import chat_completion

async def generate_procurement_plan(chat_history: List[Dict[str, str]], model_name: str = "openai",) -> Dict[str, Any]:
    """
    Generate a procurement plan from chat history.
    Output is well-structured JSON.
    """
    
    goal = await extract_goal(chat_history, model_name=model_name)
    chat_text = format_chat_history(chat_history)
    
    system_prompt = """
    You are an AI that generates a procurement plan (shopping plan) based on chat history.
    
    You MUST output **valid JSON only** with:
    
    {
        "goal": "<string>",
        "summary": "<string>",
        "items": [
            {
            "name": "<string>",
            "quantity": "<string or number>",
            "notes": "<string>"
            }
        ],
        "narrative": "<human readable text>"
    }
    
    Rules:
    - JSON only no explanation.
    - narrative must be friendly
    """
    
    user_prompt = f"""
    Goal detected: {goal}
    Chat history:
    {chat_text}
    
    Generate the procurement plan in JSON:
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = await chat_completion(messages, model_name=model_name)
    data = extract_json(raw)
    
    return {
        "goal": data.get("goal", goal),
        "summary": data.get("summary", ""),
        "items": data.get("items", []),
        "narrative": data.get("narative", "Here is your procurement summary!")
    }