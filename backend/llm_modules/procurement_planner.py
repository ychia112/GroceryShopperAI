import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import extract_json


async def generate_restock_plan(low_stock_items, grocery_items, model_name:str = "openai"):
    """
    Inventory-based retock
    Generate AI-powered weekly restock plan using inventory + grocery catalog.
    """
    
    system_prompt = """
    You are an AI Procurement Planner for a restaurant.
    
    IMPORTANT:
    - Low-stock items are ALREADY identified.
    - Produce a shopping plan ONLY for these items.
    - Grocery_items list is pre-filtered; do NOT invent items.

    JSON OUTPUT:
    {
        "goal": "",
        "summary": "<string>",
        "narrative": "<string>",
        "items": [
            {
                "name": "<string>",
                "quantity": "<string or number>",
                "notes": "<string>"
            }
        ]
    }
    """
    
    
    user_payload = {
        "low_stock": low_stock_items,
        "grocery_items": grocery_items
    }
    
    raw = await chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, indent=2)}
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