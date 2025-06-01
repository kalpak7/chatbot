import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

def main():
    print("[INFO] Loading sentence-transformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("[INFO] Connecting to database...")
    conn = sqlite3.connect("faq_db.db")
    cursor = conn.cursor()

    print("[INFO] Fetching answers without embeddings...")
    cursor.execute("SELECT id, answer FROM faqs WHERE embedding IS NULL OR embedding = ''")
    rows = cursor.fetchall()

    print(f"[INFO] Found {len(rows)} entries to process.")
    for faq_id, answer in rows:
        embedding = model.encode([answer])[0]
        emb_bytes = embedding.astype(np.float32).tobytes()
        cursor.execute("UPDATE faqs SET embedding = ? WHERE id = ?", (emb_bytes, faq_id))

    conn.commit()
    conn.close()
    print("[INFO] Embedding generation complete.")

if __name__ == "__main__":
    main()
