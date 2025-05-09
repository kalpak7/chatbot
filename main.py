
# Import necessary modules
from flask import Flask, render_template, request
import pdfplumber  # To extract text from PDF files
import faiss       # Facebook AI Similarity Search (for fast retrieval)
import numpy as np # Numerical operations (arrays)
from sentence_transformers import SentenceTransformer # Embedding model
import requests    # To call the Groq AI API
import re

# Initialize Flask app
app = Flask(__name__)

# Global variables to hold data
uploaded_text = ""   # Full text extracted from uploaded file
texts = []           # Text chunks (for embeddings)
index = None         # FAISS index
faqs = []            # Generated FAQs list

# Your Groq API key (free API key)
GROQ_API_KEY = "you_api_key"  # Replace with your actual API key
GROQ_MODEL = "llama3-70b-8192"      # You can change to "llama3-8b-8192" for faster, cheaper responses

# Load pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Home route
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", file_uploaded=False)

# File upload route
@app.route("/upload", methods=["POST"])
def upload():
    global uploaded_text, texts, index, faqs
    file = request.files["file"]

    # Extract text from uploaded file
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        return render_template("index.html", file_uploaded=False, faqs=[], error="File not in PDF or TXT format.")

    # Split text into chunks (500 characters each)
    texts = [uploaded_text[i:i+500] for i in range(0, len(uploaded_text), 500)]

    # Encode text chunks to get embeddings
    embeddings = model.encode(texts)
    dimension = embeddings.shape[1]

    # Create FAISS index and add embeddings
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    # Generate FAQs using Groq
    faqs = generate_faqs(uploaded_text)

    return render_template("index.html", file_uploaded=True, faqs=faqs)

# Question answering route
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    answer = ""
    if question:
        answer = answer_question(question)
    return render_template("index.html", file_uploaded=True, answer=answer, faqs=faqs)

# Use FAISS to find the most relevant text chunk and generate an answer
def answer_question(question):
    q_emb = model.encode([question])
    _, I = index.search(np.array(q_emb), k=1)
    context = texts[I[0][0]]
    return ask_ai(context, question)

# Function to query Groq LLaMA 3 model
def ask_ai(context, question):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You're a helpful assistant that explains error logs and helps fix code issues."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    return "Sorry, I couldn't get an answer from Groq."

# Function to generate FAQs from uploaded document
def generate_faqs(text):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Based on the following document, generate 6 helpful FAQs with answers.\n\nDocument:\n{text}\n\nFormat:\nQ: ...\nA: ..."
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are an assistant that summarizes documents into FAQs."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    faqs = []
    if res.status_code == 200:
        content = res.json()['choices'][0]['message']['content']
        for block in content.strip().split("Q:")[1:]:
            if "A:" in block:
                q, a = block.strip().split("A:", 1)
                q = q.strip()
                a = re.sub(r'\d+\.\s*$', '', a.strip()).strip()
                faqs.append((q, a))
    return faqs

# Run the app
if __name__== "__main__":
    app.run(debug=True)