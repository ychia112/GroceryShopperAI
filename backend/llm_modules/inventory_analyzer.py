import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import format_chat_history, extract_json

async def analyze_inventory(inventory_items, low_stock_items, healthy_items, grocery_items, chat_history: List[Dict[str, str]] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    LLM Inventory Analyzer
    Analyze current inventory and generate restock suggestions.
    - inventory_items: list of dicts from DB
    """
    
    chat_text = format_chat_history(chat_history) if chat_history else ""
    
    system_prompt = """
    You are an Inventory Analyst.

    IMPORTANT:
    - Low-stock / healthy classification is ALREADY computed by the backend.
    - DO NOT recalculate stock status.
    - Only generate narrative and confirm the structure.
    - Grocery items are already matched; do NOT invent items.

    JSON ONLY:
    {
        "narrative": "<string>",
        "low_stock": [...],
        "healthy": [...]
    }
    """
    
    user_payload = {
        "inventory_items": inventory_items,
        "low_stock": low_stock_items,
        "healthy": healthy_items,
        "grocery_items": grocery_items,
        "chat_history": chat_text
    }
    
    raw = await chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, indent=2)},
    ], model_name=model_name)
    
    parsed = extract_json(raw)
    
    return {
        "narrative": parsed.get("narrative", "Inventory analysis generated."),
        "low_stock": low_stock_items,
        "healthy": healthy_items
    }