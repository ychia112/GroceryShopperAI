import json
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llm import chat_completion
from llm_modules.llm_utils import format_chat_history, extract_json
from db import Inventory

async def analyze_inventory(user_id: int, chat_history: List[Dict[str, str]], session: AsyncSession, model_name: str = "openai") -> Dict[str, Any]:
    """
    Analyze current inventory and generate restock suggestions.
    """
    
    # Load inventory for this user
    res = await session.execute(
        select(Inventory).where(Inventory.user_id == user_id)
    )
    items = res.scalars().all()
    
    inventory_data = [
        {
            "product_name": item.product_name,
            "stock": item.stock,
            "safety_stock_level": item.safety_stock_level
        }
        for item in items
    ]
    
    chat_text = format_chat_history(chat_history)
    
    system_prompt = """
    You are an AI expert Inventory Analyst for a grocery store or restaurant.
    
    Your responsibilities:
    1. Detect low-stock or critically low items
    2. Suggest recommended reorder quantities
    3. Summarize inventory health

    Return JSON ONLY:
    {
    "narrative": "<human friendly summary>",
    "low_stock": [
        {
            "product_name": "...",
            "stock": <int>,
            "safety_stock": <int>,
            "status": "low" | "critical",
            "recommended_restock_qty": <int>
        }
    ],
    "healthy": [
        {
            "product_name": "...",
            "stock": <int>,
            "safety_stock": <int>
        }
    ]
    }
    """
    
    user_prompt = f"Here is the inventory:\n{json.dumps(inventory_items, indent=2)}\nAnalyze it."
    
    raw = await chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], model_name=model_name)
    
    try:
        return json.loads(raw)
    except:
        return {"narrative": raw, "low_stock": [], "healthy": []}