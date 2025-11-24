import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import extract_json, format_chat_history


async def generate_menu(inventory_items, grocery_items, chat_history: List[Dict[str, str]] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    Generate recommended dishes based on:
    - User inventory (Curreent Stock)
    - Grocery_items catalog (Vector Search Results containing Real Products)
    - Chat context
    """
    chat_text = format_chat_history(chat_history) if chat_history else ""
    
    system_prompt = """
    You are an AI Executive Chef for a restaurant.
    
    INPUT DATA:
    1. "inventory_items": What the user currently has in the kitchen.
    2. "grocery_items": A list of REAL-WORLD PRODUCTS found via Vector Search that match the user's inventory.

    YOUR TASK:
    Create a menu of 3-5 realistic dishes based on the current inventory.
    
    FOR EACH DISH:
    1. Name the dish.
    2. List "ingredients_used" (from inventory).
    3. List "missing_ingredients" (what needs to be bought).
    4. Fill "suggested_suppliers_needed":
       - Check "grocery_items" to see if there is a specific product match for the missing ingredient.
       - If yes, use the EXACT "title" and "price" from the list.
       - If no match found in grocery_items, leave it empty or list a generic name.

    JSON OUTPUT STRUCTURE:
    {
        "narrative": "Brief, appetizing summary of the menu.",
        "dishes": [
            {
                "name": "<Dish Name>",
                "ingredients_used": ["<item from inventory>", ...],
                "missing_ingredients": ["<generic name>", ...],
                "suggested_suppliers_needed": [
                    {
                        "product_name": "<EXACT title from grocery_items>",
                        "price": <float>,
                        "reason": "Best match for <missing ingredient>"
                    }
                ]
            }
        ]
    }

    RULES:
    - Output ONLY valid JSON.
    - Do NOT hallucinate products. Only use products present in "grocery_items" for the suggested_suppliers_needed field.
    - If a missing ingredient is simple (like "Salt" or "Water") and not in the list, just ignore it in supplier list.
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