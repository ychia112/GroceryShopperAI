import json
from typing import List, Dict, Any

from llm import chat_completion


async def generate_menu(inventory_items: List[Dict], model_name: str = "openai"):
    """
    Generate recommended dishes based on what ingredients are available.
    """
    
    system_prompt = """
    You are an AI Chef for a restaurant.
    You suggest dishes that can be made using the given inventory.
    
    Output JSON ONLY:
    {
        "narrative": "<short explanation>",
        "dishes": [
            {
                "name": "<dish name>",
                "ingrdients_used": ["tomatoes", "cheese"], 
                "missing_ingredients": ["basil"],
                "suggested_suppliers_needed": ["basil"]
            }
        ]
    }
    """
    
    user_prompt = f"Available ingredients:\n{json.dumps(inventory_items, indent=2)}\nGenerate possible dishes."
    
    raw = await chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], model_name=model_name)
    
    try:
        return json.loads(raw)
    except:
        return {"narrative": raw, "low_stock": [], "healthy": []}