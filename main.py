# Import necessary modules
from flask import Flask, render_template, request
import pdfplumber  # To extract text from PDF files
import faiss       # Facebook AI Similarity Search (for fast retrieval)
import numpy as np # Numerical operations (arrays)
from sentence_transformers import SentenceTransformer # Embedding model
import requests    # To call the OpenRouter AI API
import re

# Initialize Flask app
app = Flask(__name__)

# Global variables to hold data
uploaded_text = ""   # Full text extracted from uploaded file
texts = []           # Text chunks (for embeddings)
index = None         # FAISS index
faqs = []            # Generated FAQs list

# Your OpenRouter API key (free API key)
OPENROUTER_API_KEY = "Your_API_Key"  # Replace with your actual API key

# Load pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Home route
@app.route("/", methods=["GET"])
def home():
    # Render the upload form initially
    return render_template("index.html", file_uploaded=False)

# File upload route
@app.route("/upload", methods=["POST"])
def upload():
    global uploaded_text, texts, index, faqs
    file = request.files["file"]

    # Extract text from uploaded file
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            # Merge all pages' text into one string
            uploaded_text = "\n".join(page.extract_text() for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        # Read text file directly
        uploaded_text = file.read().decode("utf-8")
    else:
        # Return to the home page with an error message
        return render_template("index.html", file_uploaded=False, faqs=[], error="File not in PDF or TXT format.")

    # Split text into small chunks (500 characters each)
    texts = [uploaded_text[i:i+500] for i in range(0, len(uploaded_text), 500)]

    # Encode each chunk to get embeddings
    embeddings = model.encode(texts)
    dimension = embeddings.shape[1]  # Embedding dimension

    # Create FAISS index and add the embeddings
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    # Auto-generate FAQs from the uploaded text
    faqs = generate_faqs(uploaded_text)

    # Render the page again with the uploaded content and FAQs
    return render_template("index.html", file_uploaded=True, faqs=faqs)

# Question answering route
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    answer = ""
    if question:
        # If user asked a question, generate an answer
        answer = answer_question(question)
    # Render the page again with answer and FAQs
    return render_template("index.html", file_uploaded=True, answer=answer, faqs=faqs)

# Find best matching chunk and answer the question
def answer_question(question):
    # Encode the question
    q_emb = model.encode([question])
    # Search for closest matching chunk in FAISS index
    _, I = index.search(np.array(q_emb), k=1)
    context = texts[I[0][0]]  # Retrieve best matching chunk
    # Ask the AI model based on the context
    return ask_ai(context, question)

# Function to ask OpenRouter AI API
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
    # Send POST request to OpenRouter API
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        # Return the answer from the API response
        return res.json()['choices'][0]['message']['content']
    return "Sorry, I couldn't get an answer."

# Function to automatically generate FAQs
def generate_faqs(text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Based on the following document, generate 6 FAQs with answers:\n\n{text}\n\nFormat:\nQ: ...\nA: ..."
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }
    # Send POST request to OpenRouter API
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    faqs = []
    if res.status_code == 200:
        # Extract the questions and answers from the API response
       content = res.json()['choices'][0]['message']['content']

       for block in content.strip().split("Q:")[1:]:
           q, a = block.strip().split("A:")
           q = q.strip()
           a = re.sub(r'\d+\.\s*$', '', a.strip()).strip()  # Remove trailing numbers like '2.'
           faqs.append((q, a))
    return faqs

# Run the app in debug mode
if __name__ == "__main__":
    app.run(debug=True)
