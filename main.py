import pdfplumber
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import requests

# OpenRouter API key
OPENROUTER_API_KEY = "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"

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Read and extract text from file
def load_file(file_path):
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError("Unsupported file format. Use .pdf or .txt")

# Split text into chunks
def chunk_text(text, chunk_size=500):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# Create FAISS index
def create_index(chunks):
    embeddings = model.encode(chunks)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    return index, embeddings

# Ask OpenRouter AI with context
def ask_ai(context, question):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Answer the user's question based on the given context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"}
        ]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    return "Sorry, I couldn't get an answer."

# Main interactive loop
def main():
    file_path = input("Enter the path to a .pdf or .txt file: ").strip()
    text = load_file(file_path)
    chunks = chunk_text(text)
    index, _ = create_index(chunks)

    print("\nFile loaded. You can now ask questions (type 'exit' to quit).")
    while True:
        question = input("\nYour question: ").strip()
        if question.lower() == "exit":
            break
        q_emb = model.encode([question])
        _, I = index.search(np.array(q_emb), k=1)
        best_context = chunks[I[0][0]]
        answer = ask_ai(best_context, question)
        print(f"\nAnswer:\n{answer}")

if __name__ == "__main__":
    main()
