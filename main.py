from flask import Flask, render_template, request
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pdfplumber  # For PDF text extraction
import requests  # To make requests to OpenRouter API

# Initialize Flask app
app = Flask(__name__)

# Initialize the model for sentence embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global variables
index = None
texts = []  # Holds the raw text
uploaded_text = ""  # To store the uploaded text
faq_threshold = 2  # FAQ will be shown if the question frequency exceeds this number
OPENROUTER_API_KEY = "Your Api Key"  # Replace with your OpenRouter API key

# Database initialization function
def init_db():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT,
                        answer TEXT,
                        frequency INTEGER,
                        embedding BLOB)''')
    conn.commit()
    conn.close()

# Helper function to store question and its answer in the database
def store_question(question, answer, embedding):
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()

    # Check if the question is already in the database
    cursor.execute('SELECT id, frequency FROM questions WHERE question = ?', (question,))
    result = cursor.fetchone()
    
    if result:
        # Update frequency of existing question
        cursor.execute('UPDATE questions SET frequency = frequency + 1 WHERE id = ?', (result[0],))
    else:
        # Insert new question and frequency = 1
        cursor.execute('INSERT INTO questions (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)', 
                       (question, answer, 1, embedding.tobytes()))
    
    conn.commit()
    conn.close()

# Helper function to get FAQs based on frequency threshold
def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, answer FROM questions WHERE frequency >= ?', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()
    return faqs

# Function to extract text from uploaded file (PDF/TXT)
def extract_text_from_file(file):
    global uploaded_text
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        raise ValueError("File format not supported. Please upload a PDF or TXT file.")

# Function to ask OpenRouter API for the answer
def ask_openrouter_api(context, question):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistralai/mistral-7b-instruct",  # OpenRouter's model
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}\nAnswer:"}
        ]
    }
    
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return "Sorry, I couldn't retrieve an answer."

# Home route
@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()  # Get FAQs for display
    return render_template("index.html", faqs=faqs, file_uploaded=False)

# File upload route
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    try:
        extract_text_from_file(file)
        # Split the extracted text into chunks (for embedding)
        global texts
        texts = [uploaded_text[i:i + 500] for i in range(0, len(uploaded_text), 500)]

        # Encode each chunk to get embeddings
        embeddings = model.encode(texts)
        dimension = embeddings.shape[1]  # Embedding dimension

        # Create FAISS index and add the embeddings
        global index
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings))

        faqs = get_faqs()  # Update FAQs
        return render_template("index.html", file_uploaded=True, faqs=faqs)
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=f"Error: {str(e)}")

# Ask route - for user to ask questions
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    answer = ""

    if question:
        # Get the best matching text chunk from the file
        q_emb = model.encode([question])
        _, I = index.search(np.array(q_emb), k=1)
        context = texts[I[0][0]]  # Retrieve the best matching chunk
        
        # Ask OpenRouter for the answer
        answer = ask_openrouter_api(context, question)

        # Store the question along with the answer and its embedding in the database
        question_embedding = model.encode([question])
        store_question(question, answer, question_embedding)

    faqs = get_faqs()  # Update FAQs
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

# Initialize the database when the app starts
init_db()

if __name__ == "__main__":
    app.run(debug=True)
