import os
import sqlite3
import json
import asyncio
from sqlalchemy import select
from tqdm.asyncio import tqdm  # Recommended for progress visualization

# Import your existing modules
from db import SessionLocal, GroceryItem
from llm import get_embedding

# --- Configuration ---
# Save the sqlite file in the same directory as this script
EMBED_DB_PATH = os.path.join(os.path.dirname(__file__), "embeddings.sqlite")

# Batch size for SQLite inserts (improves disk I/O performance)
BATCH_SIZE = 50 

# Limit concurrent API calls to OpenAI to avoid Rate Limit errors (429)
CONCURRENCY_LIMIT = 10 

# SQL to create the local embeddings table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS grocery_item_embeddings (
    grocery_item_id INTEGER PRIMARY KEY,
    embedding TEXT NOT NULL
);
"""

async def process_item(semaphore, item):
    """
    Worker function to process a single grocery item.
    1. Acquires a semaphore slot.
    2. Calls OpenAI API to get the embedding.
    3. Returns the result tuple for insertion.
    """
    async with semaphore:
        try:
            # Combine title and sub_category for richer semantic search context
            text_to_embed = f"{item.title} | {item.sub_category}"
            
            # Call the LLM module (calls OpenAI text-embedding-3-large)
            emb = await get_embedding(text_to_embed)
            
            # Basic validation
            if not emb or not isinstance(emb, list):
                print(f"⚠️ Warning: No embedding returned for item ID {item.id} ({item.title})")
                return None
            
            # Return tuple: (id, json_string_embedding, title_for_logging)
            return (item.id, json.dumps(emb), item.title)
            
        except Exception as e:
            print(f"❌ Error embedding item ID {item.id} ({item.title}): {e}")
            return None

async def generate_and_store_embeddings():
    print(f"🚀 Starting embedding generation logic...")
    print(f"📂 Target Database: {EMBED_DB_PATH}")

    # 1. Initialize SQLite Database
    conn = sqlite3.connect(EMBED_DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()

    # 2. Check for existing embeddings to allow resuming if interrupted
    existing_ids = set(
        row[0] for row in conn.execute("SELECT grocery_item_id FROM grocery_item_embeddings")
    )
    print(f"📋 Found {len(existing_ids)} existing vectors in SQLite. These will be skipped.")

    # 3. Load Source Data from MySQL (Cloud SQL)
    print("📥 Fetching grocery items from MySQL...")
    async with SessionLocal() as session:
        res = await session.execute(select(GroceryItem))
        all_items = res.scalars().all()

    # Filter out items that are already processed
    items_to_process = [g for g in all_items if g.id not in existing_ids]
    print(f"⚡ Total items to process: {len(items_to_process)}")

    if not items_to_process:
        print("✅ All items are already embedded. Nothing to do.")
        conn.close()
        return

    # 4. Prepare Concurrency Tools
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []

    # Create async tasks for all items
    for item in items_to_process:
        task = process_item(semaphore, item)
        tasks.append(task)

    # 5. Execute Tasks and Batch Write to SQLite
    pending_inserts = []
    
    # process tasks as they complete
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Generating Embeddings"):
        result = await f
        
        if result:
            pending_inserts.append(result)

        # Write to DB when batch size is reached
        if len(pending_inserts) >= BATCH_SIZE:
            # Prepare data for executemany: [(id, embedding_json), ...]
            data_to_insert = [(r[0], r[1]) for r in pending_inserts]
            
            conn.executemany(
                "INSERT INTO grocery_item_embeddings (grocery_item_id, embedding) VALUES (?, ?)",
                data_to_insert
            )
            conn.commit()
            pending_inserts = [] # Clear the buffer

    # 6. Insert any remaining items in the buffer
    if pending_inserts:
        data_to_insert = [(r[0], r[1]) for r in pending_inserts]
        conn.executemany(
            "INSERT INTO grocery_item_embeddings (grocery_item_id, embedding) VALUES (?, ?)",
            data_to_insert
        )
        conn.commit()

    # 7. Final Cleanup
    conn.close()
    print("🎉 Embedding generation complete!")
    print("-" * 50)
    print(f"👉 Next Step: Upload the generated file to GCS so Cloud Run can access it:")
    print(f"   gsutil cp {EMBED_DB_PATH} gs://groceryshopperai-embeddings/embeddings.sqlite")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(generate_and_store_embeddings())