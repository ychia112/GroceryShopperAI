import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import extract_json, format_chat_history


async def generate_menu(inventory_items, grocery_items, chat_history: List[Dict[str, str]] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    Generate recommended dishes based on:
    - User inventory
    - Grocery_items catalog
    - Chat context
    """
    chat_text = format_chat_history(chat_history) if chat_history else ""
    
    system_prompt = """
    You are an AI Executive Chef for a restaurant.
    
    Your tasks:
    - Suggest realistic dishes the user can cook TODAY.
    - Prefer using ingredients already available in inventory.
    - Identify missing ingredients.
    - Suggest substitutions.
    - Recommend grocery items from the provided grocery_items list.

    RULES:
    - Output ONLY valid JSON.
    - Do NOT add explanations outside of JSON.
    - Use EXACT keys:
        "ingredients_used"
        "missing_ingredients"
        "recommended_grocery_items"
    
    IMPORTANT
    - You MUST output VALID JSON ONLY.
    - The grocery_items list is already filtered to relevant products. You MUST NOT invent any items outside the list.
    - "narrative" must be human-friendly.
    
    JSON OUTPUT:
    {
        "narrative": "<string>",
        "dishes": [
            {
                "name": "<string>",
                "ingredients_used": [...],
                "missing_ingredients": [...],
                "suggested_suppliers_needed": [...]
            }
        ]
    }
    """
    
    user_payload = {
        "inventory_items": inventory_items,
        "grocery_items": grocery_items,
        "chat_history": chat_text
    }
    
    
    raw = await chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, indent=2)},
        ],
        model_name=model_name,
    )
    
    parsed = extract_json(raw)
    
    return {
        "narrative": parsed.get("narrative", "Menu suggestions generated."),
        "dishes": parsed.get("dishes", []),
    }