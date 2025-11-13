import json
from typing import List, Dict, Any

from llm import chat_completion

def format_chat_history(chat_history: List[Dict[str, str]]) -> str:
    # Convert chat history into readable multi-line text for prompting.
    return "\n".join([f"- {m['role']}: {m['content']}" for m in chat_history])

def extract_json(text: str) -> Dict[str, Any]:
    # Attempts to parse JSON from LLM output, falling back gracefully.
    try: 
        return json.loads(text)
    except Exception:
        pass
    
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
        
    return {}


async def extract_goal(chat_history: List[Dict[str, str]], model_name: str = "openai",) -> str:
    """
    Extract the event goal from chat history using LLM.
    If none found, returns "".
    """
    chat_text = format_chat_history(chat_history)
    
    system_prompt = """
    You are an AI assistant. Identify the main event goal of the group based on the chat history.
    
    The goal could be things like:
    - "BBQ party this Saturday"
    - "Friendsgiving dinner"
    - "Weekly grocery shopping"
    - "Hotpot night with friends"
    
    Output JSON ONLY:
    {
        "goal": "<string>"
    }
    
    If there is no clear goal, return:
    {
        "goal": ""
    }
    """
    
    user_prompt = f"Chat history:\n{chat_text}\n\nExtract the goal in JSON."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = await chat_completion(messages, model_name=model_name)
    data = extract_json(raw)
    return data.get("goal", "")

async def extract_assigned_members(chat_history: List[Dict[str, str]], members: List[str], model_name: str = "openai",) -> List[str]:
    """
    Let LLM decide which members from the list have been assigned tasks based on the chat history.
    Only names present in `members` will be kept.
    """
    chat_text = format_chat_history(chat_history)
    
    system_prompt = """
    You detect which members from the given list have been assigned tasks based on the chat history.
    
    Output JSON ONLY:
    {
        "asssigned": ["name1", "name2"]
    }
    
    Rules:
    - Only include names that appear in the provided member list.
    - If nobody is clearly assigned, return an empty list.
    """
    
    user_prompt = f"""
    Chat history:
    {chat_text}
    
    Member list: {", ".join(members)}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    raw = await chat_completion(messages, model_name=model_name)
    data = extract_json(raw)
    
    assigned = data.get("assigned", [])
    # Make sure returning the name in members
    return [m for m in assigned if m in members]

def get_available_members(members: List[str], assigned: List[str]) -> List[str]:
    # Return members who are not yet assigned.
    return [m for m in members if m not in assigned]