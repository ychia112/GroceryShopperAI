from sqlalchemy import select
from db import GroceryItem

async def get_relevant_grocery_items(session, product_name: str, limit: int = 20):
    """
    Try to find grocery items relevant to the inventory product.
    Matching priority:
    1. title LIKE %product_name%
    2. sub_category LIKE %product_name%
    3. top rated items (fallback)
    """

    # 1. Title-based matching
    q1 = await session.execute(
        select(GroceryItem)
        .where(GroceryItem.title.ilike(f"%{product_name}%"))
        .limit(limit)
    )
    items1 = q1.scalars().all()
    if items1:
        return items1

    # 2. sub_category fallback
    q2 = await session.execute(
        select(GroceryItem)
        .where(GroceryItem.sub_category.ilike(f"%{product_name}%"))
        .limit(limit)
    )
    items2 = q2.scalars().all()
    if items2:
        return items2

    # 3. final fallback → top-rated items
    q3 = await session.execute(
        select(GroceryItem)
        .order_by(GroceryItem.rating_value.desc())
        .limit(limit)
    )
    return q3.scalars().all()
