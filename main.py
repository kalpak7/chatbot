import os
import sqlite3
import numpy as np
import warnings
from flask import Flask, render_template, request
import pdfplumber
import requests

app = Flask(__name__)

# Constants
GROQ_MODEL = "llama3-70b-8192"
faq_threshold = 2
uploaded_text = ""


def get_groq_api_key():
    key = os.getenv('GROQ_API_KEY')
    if not key:
        warnings.warn("GROQ_API_KEY environment variable not set. API calls will fail.")
    return key


def init_db():
    conn = sqlite3.connect("faq_db.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            frequency INTEGER,
            embedding BLOB
        )
    ''')
    conn.commit()
    conn.close()


def get_faqs():
    conn = sqlite3.connect("faq_db.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ''",
        (faq_threshold,)
    )
    faqs = cursor.fetchall()
    conn.close()
    return faqs


def extract_text_from_file(file):
    global uploaded_text
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        raise ValueError("Unsupported file format. Use PDF or TXT.")


def ask_groq_api(context, question):
    api_key = get_groq_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"Context: {context}\nQuestion: {question}\nAnswer:"
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Provide short, clear answers for FAQ purposes."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.ok:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Sorry, no answer could be generated."


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", faqs=get_faqs(), file_uploaded=False)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    try:
        extract_text_from_file(file)
        return render_template("index.html", file_uploaded=True, faqs=get_faqs())
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e))


@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()
    answer = ""
    if question and uploaded_text:
        answer = ask_groq_api(uploaded_text, question)

        # Embedding generation skipped at runtime
        # No DB update — you could log answers if needed separately
        # store_answer_and_generate_faq(answer, dummy_embedding)

    return render_template("index.html", answer=answer, file_uploaded=True, faqs=get_faqs())


if __name__ == "__main__":
    app.run(debug=True)
