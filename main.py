# Import required modules
from flask import Flask, render_template, request
import sqlite3
import numpy as np
import pdfplumber
import requests
import os

# Flask app
app = Flask(__name__)

# Global variables
uploaded_text = ""
faq_threshold = 2
GROQ_API_KEY = "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"  # Replace with your actual API key
GROQ_MODEL = "llama3-70b-8192"

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            frequency INTEGER)
    ''')
    conn.commit()
    conn.close()

# Generate question from answer using Groq
def generate_question_from_answer(answer):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Create a short, clear, FAQ-style question that would be answered by this:\n\n{answer}"
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You generate FAQ-style questions from answers."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Frequently asked question"

# Store answer and manage FAQ entries
def store_answer_and_generate_faq(answer):
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()

    # Check for similar existing answer
    cursor.execute("SELECT id, answer, frequency FROM faqs")
    all_rows = cursor.fetchall()

    matched = False
    for row in all_rows:
        q_id, existing_answer, freq = row
        if existing_answer.strip().lower() == answer.strip().lower():
            cursor.execute('UPDATE faqs SET frequency = frequency + 1 WHERE id = ?', (q_id,))
            matched = True
            break

    if not matched:
        cursor.execute('INSERT INTO faqs (question, answer, frequency) VALUES (?, ?, ?)',
                       ("", answer, 1))

    # Generate questions for high-frequency answers
    cursor.execute('SELECT id, answer, frequency FROM faqs WHERE frequency >= ? AND question = ""', (faq_threshold,))
    for row in cursor.fetchall():
        faq_id, faq_answer, _ = row
        generated_q = generate_question_from_answer(faq_answer)
        cursor.execute('UPDATE faqs SET question = ? WHERE id = ?', (generated_q, faq_id))

    conn.commit()
    conn.close()

# Retrieve all finalized FAQs
def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ""', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()
    return faqs

# Extract text from uploaded file
def extract_text_from_file(file):
    global uploaded_text
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        raise ValueError("Unsupported file format. Use PDF or TXT.")

# Ask question using Groq with context
def ask_groq_api(context, question):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You're a helpful assistant that explains error logs and helps fix code issues and you will provide error name and step by step solution to how to solve them and it should not go more than 3 lines."
            },
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}\nAnswer:"}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Sorry, I couldn't generate an answer."

# Flask routes
@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()
    return render_template("index.html", faqs=faqs, file_uploaded=False)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    try:
        extract_text_from_file(file)
        faqs = get_faqs()
        return render_template("index.html", file_uploaded=True, faqs=faqs)
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e))

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    answer = ""
    if question and uploaded_text:
        answer = ask_groq_api(uploaded_text, question)
        store_answer_and_generate_faq(answer)

    faqs = get_faqs()
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

# Initialize DB on start
init_db()

if __name__ == "__main__":
    app.run(debug=True)
