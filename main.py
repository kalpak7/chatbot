from flask import Flask, render_template, request
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pdfplumber
import requests
import os
import warnings

app = Flask(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')

index = None
texts = []
uploaded_text = ""
faq_threshold = 2
GROQ_MODEL = "llama3-70b-8192"

def get_groq_api_key():
    key =os.getenv("GROQ_API_KEY")
    if not key:
        warnings.warn("GROQ_API_KEY environment variable not set. API calls will fail.")
    return key


def init_db():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            frequency INTEGER,
            embedding BLOB)
    ''')
    conn.commit()
    conn.close()


def cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot / (norm1 * norm2)


def extract_text_from_file(file):
    global uploaded_text
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        uploaded_text = file.read().decode("utf-8")
    else:
        raise ValueError("Unsupported file format. Use PDF or TXT.")
    return uploaded_text


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
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide short, clear answers for FAQ purposes."
            },
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Sorry, I couldn't generate an answer."


def generate_question_from_answer(answer):
    return ask_groq_api(answer, "Give a short FAQ-style question for this answer")


def store_answer_and_generate_faq(answer, embedding, threshold=faq_threshold):
    conn = sqlite3.connect("faq_db.db")
    cursor = conn.cursor()
    emb = np.array(embedding)[0]

    cursor.execute("SELECT id, answer, frequency, embedding FROM faqs")
    for row in cursor.fetchall():
        faq_id, existing_answer, freq, stored_emb_blob = row
        if stored_emb_blob:
            stored_emb = np.frombuffer(stored_emb_blob, dtype=np.float32)
            sim = cosine_similarity(emb, stored_emb)
            if sim > 0.8:
                cursor.execute("UPDATE faqs SET frequency = frequency + 1 WHERE id = ?", (faq_id,))
                if freq + 1 >= threshold:
                    cursor.execute("UPDATE faqs SET question = answer WHERE id = ? AND question = ''", (faq_id,))
                conn.commit()
                conn.close()
                return

    # Generate a question for the FAQ
    generated_question = generate_question_from_answer(answer)

    cursor.execute(
        "INSERT INTO faqs (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)",
        (generated_question, answer, 1, emb.astype(np.float32).tobytes())
    )
    conn.commit()
    conn.close()


def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ""', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()
    return faqs


@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()
    return render_template("index.html", faqs=faqs, file_uploaded=False)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    issue_solution = ""
    try:
        text = extract_text_from_file(file)
        issue_solution = ask_groq_api(text, "What is the main issue or error in this text? Give a short and clear solution.")
        return render_template("index.html", file_uploaded=True, issue_solution=issue_solution, faqs=get_faqs())
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e), faqs=get_faqs())


@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()
    answer = ""
    if question and uploaded_text:
        answer = ask_groq_api(uploaded_text, question)
        ans_emb = model.encode([answer])
        store_answer_and_generate_faq(answer, ans_emb)

    return render_template("index.html", answer=answer, file_uploaded=True, faqs=get_faqs())


init_db()

if __name__ == "__main__":
    app.run(debug=True)
