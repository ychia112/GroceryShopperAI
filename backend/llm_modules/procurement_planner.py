import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import extract_json


async def generate_restock_plan(low_stock_items, grocery_items, model_name:str = "openai"):
    """
    Inventory-based retock
    Generate AI-powered weekly restock plan using inventory + vector search matches.
    """
    
    system_prompt = """
    You are an AI Procurement Planner for a restaurant.

    INPUT DATA:
    1. "low_stock": List of items the user needs.
    2. "grocery_items": A list of REAL catalog items found via Database Vector Search that match the low_stock items.

    YOUR TASK:
    For each item in "low_stock":
    1. Look through "grocery_items" to find the BEST matching product.
    2. Select that product as the recommendation.
    3. Use the REAL "title" and "price" from the selected grocery_item.
    4. Estimate a reasonable quantity to buy.

    OUTPUT JSON STRUCTURE:
    {
        "goal": "Restock Plan",
        "summary": "Short summary of total cost",
        "narrative": "Friendly explanation of what we are ordering and why.",
        "items": [
            {
                "name": "<EXACT title from grocery_items>",
                "quantity": <int>,
                "price_estimate": <float from grocery_items>,
                "notes": "Selected based on match with <low_stock name>"
            }
        ],
        "low_stock": [... echo input ...]
    }

    RULES:
    - If "grocery_items" has a match, you MUST use its exact Name and Price.
    - If no clear match is found in grocery_items, you may estimate, but note it.
    - JSON ONLY.
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
    
    
    parsed = extract_json(raw)

    return {
        "goal": "",
        "summary": parsed.get("summary", "Generated restock plan."),
        "narrative": parsed.get("narrative", "Here is your restock summary."),
        "items": parsed.get("items", []),
        "low_stock": parsed.get("low_stock", low_stock_items),
    }