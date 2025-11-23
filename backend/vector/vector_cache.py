import os
import json
import sqlite3
import numpy as np

# --- PATH CONFIGURATION ---
# Cloud Run uses /tmp because it's the only writable directory.
# Local development usually keeps the file in the project root.
CLOUD_PATH = "/tmp/embeddings.sqlite"
LOCAL_PATH = "./embeddings.sqlite"

# Logic: Use /tmp if it exists (Cloud Run), otherwise fallback to local file.
if os.path.exists(CLOUD_PATH):
    EMBED_DB_PATH = CLOUD_PATH
else:
    EMBED_DB_PATH = LOCAL_PATH
# --------------------------

_cached_vectors = None


def load_embeddings_into_memory():
    global _cached_vectors
    if _cached_vectors is not None:
        return _cached_vectors

    if not os.path.exists(EMBED_DB_PATH):
        print(f"[vector_cache] ERROR: Database not found at {EMBED_DB_PATH}")
        print(f"[vector_cache] Make sure app.py downloaded it to /tmp or it exists locally.")
        _cached_vectors = []
        return _cached_vectors

    print(f"[vector_cache] Loading embeddings from {EMBED_DB_PATH} ...")

    try:
        conn = sqlite3.connect(EMBED_DB_PATH)
        cursor = conn.cursor()
        # Ensure the table name matches your actual DB schema
        cursor.execute("SELECT grocery_item_id, embedding FROM grocery_item_embeddings")
        rows = cursor.fetchall()
        conn.close()

        vectors = []
        for gid, emb in rows:
            # Parse JSON string back to numpy array
            arr = np.array(json.loads(emb), dtype=np.float32)
            vectors.append((gid, arr))

        _cached_vectors = vectors
        print(f"[vector_cache] Loaded {len(vectors)} vectors into memory")
    except Exception as e:
        print(f"[vector_cache] Database error: {e}")
        _cached_vectors = []

    return _cached_vectors


def get_cached_embeddings():
    return load_embeddings_into_memory()