# Import all necessary Python libraries/modules for the app to work
from flask import Flask, render_template, request  # Flask is used to build web apps. 'render_template' loads HTML files, 'request' handles user input.
import sqlite3  # Allows the app to use SQLite database for storing FAQs
import numpy as np  # NumPy is used for working with vectors (embeddings)
from sentence_transformers import SentenceTransformer  # This is a pre-trained model to convert text into embeddings (numerical vector format)
import faiss  # FAISS is a tool to search similar vectors quickly (used for finding related content)
import pdfplumber  # Extracts text from PDF files
import requests  # Allows sending HTTP requests to external APIs like OpenRouter

# Create a new Flask web application instance
app = Flask(__name__)

# Load a small and fast pre-trained model to convert text to embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global variables (used throughout the app)
index = None  # Will hold FAISS search index (used after file upload)
texts = []  # Will store the document in 500-character chunks
uploaded_text = ""  # Holds the complete text from the uploaded document
faq_threshold = 2  # Minimum times an answer must be seen before it becomes a FAQ
OPENROUTER_API_KEY = "Your Api Key"  # API key to use the OpenRouter API

# Function to initialize the SQLite database and create the 'faqs' table
def init_db():
    conn = sqlite3.connect('faq_db.db')  # Connect to the SQLite database (creates if doesn't exist)
    cursor = conn.cursor()
    # Create a table to store FAQs (if it doesn't already exist)
    cursor.execute('''CREATE TABLE IF NOT EXISTS faqs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Auto-incrementing ID
                        question TEXT,                         -- Question part of FAQ
                        answer TEXT,                           -- Answer part
                        frequency INTEGER,                     -- How many times this answer occurred
                        embedding BLOB)''')                    # Stored embedding(asbinary)
    conn.commit()  # Save changes to the database
    conn.close()  # Close the database connection

# Function to calculate cosine similarity between two vectors (to compare meaning)
def cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)  # Dot product of vectors
    norm1 = np.linalg.norm(vec1)  # Length (magnitude) of vector 1
    norm2 = np.linalg.norm(vec2)  # Length of vector 2
    return dot / (norm1 * norm2)  # Return cosine similarity (value between -1 to 1)

# Function to generate a short FAQ-style question from a given answer using LLM
def generate_question_from_answer(answer):
    # Create a prompt that asks LLM to make a question from a given answer
    prompt = f"Create a short , mini , suitable , clear question that would be answered by this:\n\n{answer}"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",  # API key for OpenRouter
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",  # Chosen LLM model from OpenRouter
        "messages": [
            {"role": "system", "content": "You generate FAQ-style questions from answers."},
            {"role": "user", "content": prompt}
        ]
    }
    # Make a POST request to OpenRouter's API
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        # Return the generated question
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        return "Frequently asked question"  # If something goes wrong, use a default

# Function to store an answer and convert it into an FAQ if needed
def store_answer_and_generate_faq(answer, embedding):
    conn = sqlite3.connect('faq_db.db')  # Connect to the database
    cursor = conn.cursor()
    embedding_np = np.array(embedding)[0]  # Convert embedding list to numpy array

    # Fetch all stored FAQs from the database
    cursor.execute("SELECT id, question, answer, frequency, embedding FROM faqs")
    all_rows = cursor.fetchall()

    matched = False  # Flag to check if similar answer already exists

    # Compare new answer's embedding with stored ones
    for row in all_rows:
        q_id, question, existing_answer, freq, emb_blob = row
        stored_embedding = np.frombuffer(emb_blob, dtype=np.float32)  # Convert blob to vector
        sim = cosine_similarity(embedding_np, stored_embedding)  # Get similarity score

        if sim > 0.8:  # If very similar
            cursor.execute('UPDATE faqs SET frequency = frequency + 1 WHERE id = ?', (q_id,))  # Increment frequency
            matched = True
            break

    # If not matched, insert this as a new entry
    if not matched:
        cursor.execute('INSERT INTO faqs (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)',
                       ("", answer, 1, embedding_np.astype(np.float32).tobytes()))

    # For each answer where frequency is high enough but no question exists, generate one
    cursor.execute('SELECT id, answer, frequency FROM faqs WHERE frequency >= ? AND question = ""', (faq_threshold,))
    for row in cursor.fetchall():
        faq_id, faq_answer, _ = row
        generated_q = generate_question_from_answer(faq_answer)  # Generate a question
        cursor.execute('UPDATE faqs SET question = ? WHERE id = ?', (generated_q, faq_id))  # Save it

    conn.commit()  # Save all changes
    conn.close()  # Close DB connection

# Function to fetch FAQs to show on the website
def get_faqs():
    conn = sqlite3.connect('faq_db.db')  # Connect to database
    cursor = conn.cursor()
    # Get only FAQs that crossed threshold and have a question
    cursor.execute('SELECT question, answer FROM faqs WHERE frequency >= ? AND question != ""', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()  # Close connection
    return faqs  # Return list of FAQs

# Function to extract full text from uploaded file (PDF or TXT)
def extract_text_from_file(file):
    global uploaded_text  # Use the global variable
    if file.filename.endswith(".pdf"):  # If file is PDF
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)  # Combine all pages
    elif file.filename.endswith(".txt"):  # If file is TXT
        uploaded_text = file.read().decode("utf-8")  # Read and decode text
    else:
        raise ValueError("Unsupported file format. Use PDF or TXT.")  # Raise error for other file types

# Function to ask OpenRouter LLM using context and question
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
        return response.json()['choices'][0]['message']['content'].strip()  # Return answer
    else:
        return "Sorry, I couldn't generate an answer."  # Default error message

# Route for home page
@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()  # Load all FAQs from database
    return render_template("index.html", faqs=faqs, file_uploaded=False)  # Show home page

# Route to handle file upload (PDF or TXT)
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]  # Get uploaded file
    try:
        extract_text_from_file(file)  # Extract all text from it
        global texts
        # Split full text into chunks of 500 characters
        texts = [uploaded_text[i:i + 500] for i in range(0, len(uploaded_text), 500)]
        embeddings = model.encode(texts)  # Generate embeddings for each chunk

        # Create FAISS index using the embedding dimensions
        global index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings))  # Add embeddings to FAISS index

        faqs = get_faqs()
        return render_template("index.html", file_uploaded=True, faqs=faqs)  # Show success screen
    except Exception as e:
        return render_template("index.html", file_uploaded=False, error=str(e))  # Show error

# Route to handle user question
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]  # Get question typed by user
    answer = ""
    if question:
        q_emb = model.encode([question])  # Convert question to embedding
        _, I = index.search(np.array(q_emb), k=1)  # Find most similar text chunk
        context = texts[I[0][0]]  # Get text chunk as context
        answer = ask_openrouter_api(context, question)  # Get answer from LLM

        ans_emb = model.encode([answer])  # Create embedding for answer
        store_answer_and_generate_faq(answer, ans_emb)  # Store it in DB if needed

    faqs = get_faqs()  # Refresh FAQ list
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

# Initialize the database when app starts
init_db()

# Run the Flask app in debug mode (for development only)
if __name__ == "__main__":
    app.run(debug=True)
