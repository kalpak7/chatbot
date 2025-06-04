from flask import Flask, render_template, request
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pdfplumber
import requests

app = Flask(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')

index = None
texts = []
uploaded_text = ""
faq_threshold = 2
GROQ_API_KEY = "Your Api Key"

GROQ_MODEL = "llama3-70b-8192"
faq_threshold = 2
uploaded_text = ""


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


def generate_question_from_answer(answer):

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"Return only the FAQ-style question which is sutable  (no explanation) for the following answer:\n\n{answer}"
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You generate FAQ-style questions from answers. Only return the question."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Frequently asked question"

def store_answer_and_generate_faq(answer, embedding):
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    embedding_np = np.array(embedding)[0]

    cursor.execute("SELECT id, question, answer, frequency, embedding FROM faqs")
    all_rows = cursor.fetchall()

    matched = False
    for row in all_rows:
        q_id, _, existing_answer, freq, emb_blob = row
        stored_embedding = np.frombuffer(emb_blob, dtype=np.float32)
        sim = cosine_similarity(embedding_np, stored_embedding)
        if sim > 0.8:
            cursor.execute('UPDATE faqs SET frequency = frequency + 1 WHERE id = ?', (q_id,))
            matched = True
            break

    if not matched:
        cursor.execute('INSERT INTO faqs (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)',
                       ("", answer, 1, embedding_np.astype(np.float32).tobytes()))

    cursor.execute('SELECT id, answer, frequency FROM faqs WHERE frequency >= ? AND question = ""', (faq_threshold,))
    for row in cursor.fetchall():
        faq_id, faq_answer, _ = row
        generated_q = generate_question_from_answer(faq_answer)
        cursor.execute('UPDATE faqs SET question = ? WHERE id = ?', (generated_q, faq_id))

    conn.commit()
    conn.close()

def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ""', (faq_threshold,))
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
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide short, clear answers for FAQ purposes according the question asked."
            },
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}\nAnswer:"}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if res.status_code == 200:
        return res.json()['choices'][0]['message']['content'].strip()
    return "Sorry, I couldn't generate an answer."

# New function to extract issue and solution
def extract_issue_and_solution(text):
    prompt = f"""
Extract the main error or issue from the following content and provide a short and clear solution for it.
If no issue is found, say "No significant error or issue found."

Content:
{text}
"""
    return ask_groq_api("", prompt)

@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()
    return render_template("index.html", faqs=faqs, file_uploaded=False)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    try:
        extract_text_from_file(file)
        global texts
        texts = [uploaded_text[i:i + 500] for i in range(0, len(uploaded_text), 500)]
        embeddings = model.encode(texts)

        global index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings))

        # Extract issue and solution
        issue_solution = extract_issue_and_solution(uploaded_text)

        faqs = get_faqs()
        return render_template("index.html", file_uploaded=True, issue_solution=issue_solution, faqs=faqs)
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e), faqs=[])

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    answer = ""
    if question:
        q_emb = model.encode([question])
        _, I = index.search(np.array(q_emb), k=1)
        context = texts[I[0][0]]
        answer = ask_groq_api(context, question)

        ans_emb = model.encode([answer])
        store_answer_and_generate_faq(answer, ans_emb)

    faqs = get_faqs()
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

init_db()

if __name__ == "__main__":
    app.run(debug=True)
