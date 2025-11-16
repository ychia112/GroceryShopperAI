import json
from typing import List, Dict, Any

from llm import chat_completion


async def generate_restock_plan(inventory_items: List[Dict], grocery_items: List[Dict], model_name:str = "openai"):
    """
    Generate weekly procurement plan + supplier recommendations.
    """
    
    system_prompt = """
    You are an AI Procurement Planner for a restaurant.
    
    Given:
    1. current inventory
    2. grocery catalog with price + category
    
    Output JSON ONLY:
    {
        "narrative": "<short story-style explanation>",
        "restock_plan": [
            {
                "product_name: "...",
                "needed_qty": <int>,
                "recommended_supplier": "supplier name or link>",
                "price_estimate": <float>
            }
        ]
    }
    """
    
    user_prompt = f"""
    Inventory: {json.dumps(inventory_items, indent=2)}
    
    Grocery catalog sample: {json.dumps(grocery_items[:30], indent=2)}
    
    Create a weekly restock plan with suppliers.
    """
    
    raw = await chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], model_name=model_name)
    
    
    try:
        return json.loads(raw)
    except:
        return {"narrative": raw, "restock_plan": []}