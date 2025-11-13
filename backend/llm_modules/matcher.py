import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import (format_chat_history, extract_json, extract_goal, extract_assigned_members, get_available_members,)


async def suggest_invites(members: List[str], chat_history: List[Dict[str, str]], goal: str | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    Suggest role assignments or missing roles based on:
    - chat history
    - auto-extracted goal
    - auto-extracted assigned members
    - provided member list
    """
    if not goal:
        goal = await extract_goal(chat_history, model_name=model_name)
    
    assigned_members = await extract_assigned_members(chat_history, members, model_name=model_name)
    available_members = get_available_members(members, assigned_members)
    
    
    system_prompt = """
    You are an AI assistant helping a group plan an event or grocery shopping task.
    
    Output MUST be valid JSON with these structure:
    {
        "suggested_invites": ["<existing member name>"],
        "missing_roles": ["<role>"],
        "narrative": "<friendly natural-language explanation>"
    }
    
    Rules:
    - JSON ONLY. No extra commentary outside JSON.
    - Never invent people outside the provided room member list.
    - "suggested_invites" must be chosen from the available member list only.
    - If additional help is needed beyond available members, suggest the TYPE of helper in "missing_roles" (e.g., "someone who can help grill", "dessert helper").
    - "narrative" must explain the reasoning in friendly, natural language.
    """
    
    chat_text = format_chat_history(chat_history)
    
    user_prompt = f"""
    Event goal: {goal}
    
    All room members: {', '.join(members) if members else 'None'}
    Detected assigned members: {', '.join(assigned_members) if assigned_members else 'None'}
    Available members for new tasks: {', '.join(available_members) if available_members else 'None'}
    
    Chat history:
    {chat_text}
    
    Generate suggestions in JSON ONLY.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        raw = await chat_completion(messages, model_name=model_name)
        data = extract_json(raw)
        
        return {
            "suggested_invites": data.get("suggested_invites", []),
            "missing_roles": data.get("missing_roles", []),
            "narrative": data.get("narrative", "Here are some helpful suggestions.")
        }
        
    except Exception as e:
        print(f"[Matcher Error] {e}")
        return {
            "suggested_invites": [],
            "missing_roles": [],
            "narrative": "Sorry, I couldn't generate suggestions."
        }