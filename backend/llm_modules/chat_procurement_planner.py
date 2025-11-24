import json
from typing import List, Dict, Any

from llm_modules.llm_utils import (extract_goal, extract_json, format_chat_history,)
from llm import chat_completion

async def generate_procurement_plan(chat_history: List[Dict[str, str]], model_name: str = "openai",) -> Dict[str, Any]:
    """
    Chat-based procurement planner
    Generates a consolidated shopping list by analyzing user intent, resolving conflicts, and merging quantities.
    """
    
    inferred_goal = await extract_goal(chat_history, model_name=model_name)
    chat_text = format_chat_history(chat_history)
    
    system_prompt = """
    You are an intelligent AI Procurement Planner.
    
    Your goal is to create a consolidated shopping list based on the chat history.

    CRITICAL LOGIC RULES:
    1. **Conflict Resolution**: If User A asks for an item, but User B says "we already have it" or "don't buy it", REMOVE it from the list.
    2. **Quantity Merging**: If User A says "buy 2 apples" and User B says "buy 3 more", the output should be "5 apples".
    3. **Categorization**: Assign a logical category (e.g., Produce, Dairy, Meat, Household) to each item.
    4. **Filtering**: Ignore casual chit-chat. Only list items explicitly requested for purchase.

    OUTPUT FORMAT (STRICT JSON ONLY):
    {
        "goal": "<string (The extracted event or goal)>",
        "summary": "<string (A brief 1-sentence summary of the plan)>",
        "narrative": "<string (A friendly, human-like explanation of what was decided)>",
        "items": [
            {
                "name": "<string (Item Name)>",
                "quantity": "<string (e.g. '2 packs', '500g')>",
                "category": "<string (e.g. 'Produce', 'Dairy')>", 
                "notes": "<string (Who asked for it, or specific brand mentioned)>"
            }
        ]
    }
    
    IMPORTANT:
    - Output ONLY VALID JSON. 
    - Do NOT include markdown formatting like ```json ... ```.
    """

    
    user_content = json.dumps(
        {
            "inferred_goal": inferred_goal,
            "chat_history_text": chat_text,
        },
        indent=2
    )
    
    raw = await chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        model_name=model_name,
    )

    data = extract_json(raw)
    
    return {
        "goal": data.get("goal", inferred_goal),
        "summary": data.get("summary", "Shopping list generated."),
        "narrative": data.get("narrative", "Here is your consolidated shopping plan."),
        "items": data.get("items", []),
    }