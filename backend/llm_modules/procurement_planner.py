import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import extract_json


async def generate_restock_plan(inventory_items: List[Dict], grocery_items: List[Dict], model_name:str = "openai"):
    """
    Inventory-based retock
    Generate AI-powered weekly restock plan using inventory + grocery catalog.
    """
    
    system_prompt = """
    You are an AI Procurement Planner for a restaurant.
    
    Your tasks:
    - Identify items where stock < safety_stock_level.
    - Recommend restock quantity based on shortage severity.
    - Use ONLY the provided grocery_catalog_sample list.
    - Suggest supplier using grocery_items provided.
    - Estimate price from grocery_items.
    - Provide a friendly narrative.
    
    RULES:
    - Output ONLY VALID JSON.
    - No explanations outside the JSON block.
    - Use EXACT FIELD NAMES below.
    
    JSON FORMAT:
    {
        "goal": "",
        "summary": "<string>",
        "narrative": "<string>",
        "items": [
            {
                "name": "<string>",
                "quantity": <int>,
                "notes": "<string>",
                "price_estimate": <float>,
                "supplier": "<string>"
            }
        ]
    }
    """
    
    
    user_payload = json.dumps(
        {
            "inventory": inventory_items,
            "grocery_catalog_sample": grocery_items,
        }, 
        indent=2
    )
    
    raw = await chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload}
        ], 
        model_name=model_name,
    )
    
    
    data = extract_json(raw)

    return {
        "goal": "",
        "summary": data.get("summary", "Generated restock plan."),
        "narrative": data.get("narrative", "Here is your restock summary."),
        "items": data.get("items", []),
    }