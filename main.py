# Import necessary modules
from flask import Flask, render_template, request  # Flask modules for web app
import sqlite3  # For SQLite database operations
import numpy as np  # For handling embeddings and vector math
from sentence_transformers import SentenceTransformer  # To generate embeddings
import faiss  # Facebook AI Similarity Search library for semantic search
import pdfplumber  # To extract text from PDF files
import requests  # For making HTTP requests to OpenRouter API

# Initialize Flask application
app = Flask(__name__)

# Load a small and fast sentence embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global variables
index = None  # Will hold FAISS index after document upload
texts = []  # List of document chunks (500-char)
uploaded_text = ""  # Complete uploaded document text
faq_threshold = 2  # Frequency after which something becomes a FAQ
OPENROUTER_API_KEY = "your api key"  # API key for OpenRouter 

# Initialize SQLite DB with a table to store FAQs
def init_db():
    conn = sqlite3.connect('faq_db.db')  # Connect to database
    cursor = conn.cursor()
    # Create faqs table if it doesn't exist already
    cursor.execute('''CREATE TABLE IF NOT EXISTS faqs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT,
                        answer TEXT,
                        frequency INTEGER,
                        embedding BLOB)''')
    conn.commit()  # Save changes
    conn.close()  # Close connection

# Function to compute cosine similarity between two vectors
def cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)  # Dot product
    norm1 = np.linalg.norm(vec1)  # Magnitude of vec1
    norm2 = np.linalg.norm(vec2)  # Magnitude of vec2
    return dot / (norm1 * norm2)  # Cosine similarity

# Use LLM to generate a short question from an answer (used in FAQs)
def generate_question_from_answer(answer):
    prompt = f"Create a short , mini , suitable , clear question that would be answered by this:\n\n{answer}"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "You generate FAQ-style questions from answers."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()  # Return question
    else:
        return "Frequently asked question"  # Fallback

# Store answers and create FAQ question when frequency crosses threshold
def store_answer_and_generate_faq(answer, embedding):
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    embedding_np = np.array(embedding)[0]  # Get vector from list

    # Check for semantic similarity with existing answers
    cursor.execute("SELECT id, question, answer, frequency, embedding FROM faqs")
    all_rows = cursor.fetchall()

    matched = False
    for row in all_rows:
        q_id, question, existing_answer, freq, emb_blob = row
        stored_embedding = np.frombuffer(emb_blob, dtype=np.float32)  # Convert blob to vector
        sim = cosine_similarity(embedding_np, stored_embedding)  # Check similarity

        if sim > 0.8:  # If similar, increase frequency
            cursor.execute('UPDATE faqs SET frequency = frequency + 1 WHERE id = ?', (q_id,))
            matched = True
            break

    # If not matched, insert as a new answer (initial frequency = 1)
    if not matched:
        cursor.execute('INSERT INTO faqs (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)',
                       ("", answer, 1, embedding_np.astype(np.float32).tobytes()))

    # Now generate a FAQ-style question if frequency threshold is crossed and no question exists
    cursor.execute('SELECT id, answer, frequency FROM faqs WHERE frequency >= ? AND question = ""', (faq_threshold,))
    for row in cursor.fetchall():
        faq_id, faq_answer, _ = row
        generated_q = generate_question_from_answer(faq_answer)  # Use LLM to make question
        cursor.execute('UPDATE faqs SET question = ? WHERE id = ?', (generated_q, faq_id))

    conn.commit()
    conn.close()

# Retrieve FAQs from the database
def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    # Only return entries where frequency threshold is met and question is generated
    cursor.execute('SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ""', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()
    return faqs

# Extract full text from uploaded PDF or TXT file
def extract_text_from_file(file):
    global uploaded_text
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        raise ValueError("Unsupported file format. Use PDF or TXT.")

# Ask OpenRouter API using context and user question
def ask_openrouter_api(context, question):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide short, clear answers for FAQ purposes."
            },
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}\nAnswer:"}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        return "Sorry, I couldn't generate an answer."

# Route: Home Page
@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()  # Fetch all FAQs to display
    return render_template("index.html", faqs=faqs, file_uploaded=False)

# Route: Handle File Upload
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    try:
        extract_text_from_file(file)  # Extract full document text
        global texts
        # Split document into chunks of 500 characters
        texts = [uploaded_text[i:i + 500] for i in range(0, len(uploaded_text), 500)]
        embeddings = model.encode(texts)  # Generate embeddings

        # Initialize FAISS index and add vectors
        global index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings))

        faqs = get_faqs()
        return render_template("index.html", file_uploaded=True, faqs=faqs)
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e))

# Route: Handle Question Input from User
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]  # Get user input
    answer = ""
    if question:
        q_emb = model.encode([question])  # Embed the question
        _, I = index.search(np.array(q_emb), k=1)  # Search similar chunk
        context = texts[I[0][0]]  # Get best matched context
        answer = ask_openrouter_api(context, question)  # Ask LLM

        ans_emb = model.encode([answer])  # Perform semantic analysis on answer
        store_answer_and_generate_faq(answer, ans_emb)  # Store answer in DB

    faqs = get_faqs()
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

# Initialize database on app start
init_db()

# Run app in debug mode for development
if __name__ == "__main__":
    app.run(debug=True)
