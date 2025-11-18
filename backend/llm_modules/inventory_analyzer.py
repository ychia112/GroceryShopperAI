import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import format_chat_history, extract_json

async def analyze_inventory(inventory_items: List[Dict[str, Any]], grocery_items: List[Dict[str, Any]], chat_history: List[Dict[str, str]] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    LLM Inventory Analyzer
    Analyze current inventory and generate restock suggestions.
    - inventory_items: list of dicts from DB
    """
    
    chat_text = format_chat_history(chat_history) if chat_history else ""
    
    system_prompt = """
    You are an AI expert Inventory Analyst for a grocery store or restaurant.
    
    Your responsibilities:
    1. Identify items that are low or critical stock.
    2. Estimate recommended restock quantity such that:
       recommended_restock_qty = max(0, safety_stock - stock) + safety_buffer
       (safety_buffer = 1–3)
    3. Provide a friendly summary narrative.
    4. Recommend suitable grocery catalog items for restock if needed.
    
    RULES:
    - You MUST output ONLY VALID JSON.
    - Do NOT include any non-JSON text before or after JSON.
    - The grocery_items list is already a pre-filtered subset of relevant products. Do NOT invent or search for any items outside this list.
    - Grocery recommendations MUST come from the provided grocery_items list.


    JSON OUTPUT FORMAT:
    {
        "narrative": "<string>",
        "low_stock": [
            {
                "product_name": "<string>",
                "stock": <int>,
                "safety_stock": <int>,
                "status": "low" | "critical",
                "recommended_restock_qty": <int>,
                "recommended_grocery_items": [
                    {
                        "title": "<string>",
                        "price": <float>,
                        "rating": <float>
                    }
                ]
            }
        ],
        "healthy": [
            {
                "product_name": "<string>",
                "stock": <int>,
                "safety_stock": <int>
            }
        ]
    }
    """
    
    user_payload = {
        "inventory_items": inventory_items,
        "grocery_items": grocery_items,
        "chat_history": chat_text,
    }
    
    raw = await chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, indent=2)},
    ], model_name=model_name)
    
    parsed = extract_json(raw)
    
    return {
        "narrative": parsed.get("narrative", "Inventory analysis generated."),
        "low_stock": parsed.get("low_stock", []),
        "healthy": parsed.get("healthy", []),
    }