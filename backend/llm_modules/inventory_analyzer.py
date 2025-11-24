import json
from typing import List, Dict, Any

from llm import chat_completion
from llm_modules.llm_utils import format_chat_history, extract_json

async def analyze_inventory(inventory_items, low_stock_items, healthy_items, grocery_items, chat_history: List[Dict[str, str]] | None = None, model_name: str = "openai") -> Dict[str, Any]:
    """
    LLM Inventory Analyzer
    Analyze current inventory and generate restock suggestions using Vector Search results.
    """
    
    chat_text = format_chat_history(chat_history) if chat_history else ""
    
    system_prompt = """
    You are an Inventory Analyst.

    INPUT DATA EXPLANATION:
    - "low_stock": Items user currently lacks.
    - "grocery_items": Relevant products found in the catalog via Vector Search (potential matches).

    YOUR TASK:
    1. Acknowledge the current inventory status.
    2. For low_stock items, check if there are matching products in "grocery_items". 
       If yes, mention in the narrative that they are available to order (e.g., "We found matching items for your low stock tomatoes...").
    3. Output STRICT JSON.

    OUTPUT FORMAT:
    {
        "narrative": "<text summary including availability check>",
        "low_stock": [... echo input ...],
        "healthy": [... echo input ...]
    }

    RULES:
    - Do NOT change the stock numbers.
    - JSON ONLY.
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
    
    # Add helpful CTA
    final_narrative = parsed.get("narrative", "Inventory analysis generated.")
    final_narrative += " If you need a restock plan, type '@gro restock'."

    
    return {
        "narrative": final_narrative,
        "low_stock": parsed.get("low_stock", low_stock_items),
        "healthy": parsed.get("healthy", healthy_items),
    }