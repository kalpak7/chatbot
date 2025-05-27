
# Import necessary modules
from flask import Flask, render_template, request
import pdfplumber  # To extract text from PDF files
import requests    # To call the Groq AI API
import re
import os

# Initialize Flask app
app = Flask(__name__)

# Global variables to hold data
uploaded_text = ""   # Full text extracted from uploaded file
faqs = []            # Generated FAQs list

# Your Groq API key (from environment variable or hardcoded)
#GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "llama3-70b-8192"

def get_groq_api_key():
   
    key = os.getenv('GROQ_API_KEY')
    if not key:
        warnings.warn("GROQ_API_KEY environment variable not set. API calls will fail.")
    return key

# Home route
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", file_uploaded=False)

# File upload route
@app.route("/upload", methods=["POST"])
def upload():
    global uploaded_text, faqs
    file = request.files["file"]

    # Extract text from uploaded file
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        return render_template("index.html", file_uploaded=False, faqs=[], error="File not in PDF or TXT format.")

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

# Directly use the uploaded full document as context
def answer_question(question):
    return ask_ai(uploaded_text, question)

# Function to query Groq LLaMA 3 model
def ask_ai(context, question):
    GROQ_API_KEY = get_groq_api_key()
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You're a helpful assistant that explains error logs and helps fix code issues and you will provide error name and step by step solution to how to solve them and it should not go more than 3 lines."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content']
    return "Sorry, I couldn't get an answer from Groq."

# Function to generate FAQs from uploaded document
def generate_faqs(text):
    GROQ_API_KEY = get_groq_api_key()
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Based on the following document, generate 2 helpful FAQs with answers and it should be just name of the error and what we should do to solve it and shouldnt exceed 3 lines.\n\nDocument:\n{text}\n\nFormat:\nQ: ...\nA: ..."
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
if __name__ == "__main__":
    app.run(debug=True)