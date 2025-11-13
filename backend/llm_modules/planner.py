import json
from typing import List, Dict, Any
from dotenv import load_dotenv

from llm import chat_completion
from llm_modules.llm_utils import (format_chat_history, extract_json, extract_goal,)

async def generate_group_plan(chat_history: List[Dict[str, str]], goal: str | None = None, members: List[str] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    Generate a structed group plan based on chat context and goal.
    - If goal is None or empty, it will be automatically extracted from chat_history.
    - members is optional, but if provided, the model can use them for assignments.
    """
    
    if not goal:
        goal = await extract_goal(chat_history, model_name=model_name)
    
    members = members or []
    
    system_prompt = """
    You are an AI assistant that generates grocery/event planning results.

    Your output MUST be valid JSON with these fields:
    {
    "event": "<string>",
    "summary": "<short summary>",
    "items": [{"name": "<string>", "assigned_to": "<string>"}],
    "timeline": ["<string>", "<string>"],
    "narrative": "<a short natural-language explanation users can read>"
    }

    Rules:
    - JSON ONLY. No extra commentary.
    - "narrative" should sound friendly and conversational.
    - "items" must be a list of objects with "name" and "assigned_to".
    - If you know the member list, try to assign tasks to existing members.
    - If no member name fits, you may use "Unassigned".
    """
    
    chat_text = format_chat_history(chat_history)
    members_str = ", ".join(members) if members else "None"
    
    user_prompt = f"""
    Detected/Provided goal: {goal}
    
    Room members(if any): {members_str}
    
    Chat history: 
    {chat_text}
    
    Generate a structured JSON plan with all required keys.
    
    Example format:
    {{
        "event_type": "Friendsgiving Dinner",
        "summary": "Plan for a dinner with friends, coordinating dishes and drinks.",
        "items": [
            {{"name": "Turkey", "assigned_to": "Alice"}},
            {{"name": "Wine", "assigned_to": "Brian"}}
        ],
        "timeline": ["Buy ingredients by Wed", "Cook on Thu"],
        "narrative": "Here’s your Friendsgiving plan! Alice will prepare the turkey..."
    }}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        raw = await chat_completion(messages, model_name=model_name)
        data = extract_json(raw)
        
        return {
            "event": data.get("event", goal or ""),
            "summary": data.get("summary", ""),
            "items": data.get("items", []),
            "timeline": data.get("timeline", []),
            "narrative": data.get("narrative", "Here is your plan!")
        }
    except Exception as e:
        print(f"[Planner Error] {e}")
        return {
            "event": goal or "",
            "summary": "Failed to generate plan.",
            "items": [],
            "timeline": [],
            "narrative": "Sorry, I couldn't generate the plan."
        }