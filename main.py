# Import necessary modules from Flask and other libraries
from flask import Flask, render_template, request
import sqlite3  # For SQLite database operations
import numpy as np  # For numerical operations and vector handling
from sentence_transformers import SentenceTransformer  # For generating sentence embeddings
import faiss  # For similarity search using FAISS
import pdfplumber  # For extracting text from PDF files
import requests  # For making API calls

# Create Flask app
app = Flask(__name__)

# Load the pre-trained sentence embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global variables
index = None  # Will hold the FAISS index
texts = []  # Will hold chunks of uploaded document text
uploaded_text = ""  # Full extracted text from uploaded file
faq_threshold = 2  # Minimum frequency for a question to be promoted to FAQ
OPENROUTER_API_KEY = ""  # Your OpenRouter API key (keep this private)

# Function to initialize the SQLite database and table
def init_db():
    conn = sqlite3.connect('faq_db.db')  # Connect to the database
    cursor = conn.cursor()
    # Create table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT,
                        answer TEXT,
                        frequency INTEGER,
                        embedding BLOB)''')
    conn.commit()  # Save changes
    conn.close()  # Close the connection

# Function to calculate cosine similarity between two vectors
def cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)  # Dot product
    norm1 = np.linalg.norm(vec1)  # Magnitude of vec1
    norm2 = np.linalg.norm(vec2)  # Magnitude of vec2
    return dot / (norm1 * norm2)  # Cosine similarity formula

# Function to create a representative question from similar ones using LLM
def summarize_questions(question_list):
    # Create prompt with a list of questions
    prompt = "Create one short, clear, generic question that covers all of these:\n\n" + "\n".join(f"- {q}" for q in question_list)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "You generate clear, concise FAQ questions."},
            {"role": "user", "content": prompt}
        ]
    }
    # Send API request to OpenRouter
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()  # Return summarized question
    else:
        return question_list[0]  # Fallback to first question if API fails

# Function to store question and answer in the database
def store_question(question, answer, embedding):
    conn = sqlite3.connect('faq_db.db')  # Connect to DB
    cursor = conn.cursor()
    embedding_np = np.array(embedding)[0]  # Convert to numpy array

    cursor.execute("SELECT id, question, frequency, embedding FROM questions")  # Get all stored questions
    all_rows = cursor.fetchall()

    matched = False  # Flag to check for similar existing question
    for row in all_rows:
        q_id, existing_q, freq, emb_blob = row
        stored_embedding = np.frombuffer(emb_blob, dtype=np.float32)  # Decode stored embedding
        sim = cosine_similarity(embedding_np, stored_embedding)  # Compute similarity

        if sim > 0.8:  # If similarity is high enough
            representative_q = summarize_questions([existing_q, question])  # Merge question wording
            # Update existing question with new representative and increment frequency
            cursor.execute('UPDATE questions SET question = ?, frequency = frequency + 1 WHERE id = ?',
                           (representative_q, q_id))
            matched = True
            break

    # If no match found, insert as a new entry
    if not matched:
        cursor.execute('INSERT INTO questions (question, answer, frequency, embedding) VALUES (?, ?, ?, ?)',
                       (question, answer, 1, embedding_np.astype(np.float32).tobytes()))

    conn.commit()  # Save changes
    conn.close()  # Close connection

# Function to get FAQs from the database
def get_faqs():
    conn = sqlite3.connect('faq_db.db')
    cursor = conn.cursor()
    # Select only those questions with frequency above the threshold
    cursor.execute('SELECT question, answer FROM questions WHERE frequency >= ?', (faq_threshold,))
    faqs = cursor.fetchall()
    conn.close()
    return faqs  # Return list of FAQs

# Function to extract text from uploaded file (PDF or TXT)
def extract_text_from_file(file):
    global uploaded_text  # Use global variable
    if file.filename.endswith(".pdf"):
        # Use pdfplumber to extract text from each page
        with pdfplumber.open(file) as pdf:
            uploaded_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".txt"):
        # Decode and read TXT file
        uploaded_text = file.read().decode("utf-8")
    else:
        # Raise error for unsupported format
        raise ValueError("File format not supported. Please upload a PDF or TXT file.")

# Function to call OpenRouter API and get answer for a question using document context
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
                "content": "You are a helpful assistant. Provide short, crisp, and easy-to-understand answers suitable for FAQs."
            },
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}\nAnswer:"}
        ]
    }
    # Make API call
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()  # Return API response
    else:
        return "Sorry, I couldn't retrieve an answer."  # Handle error case

# Home route - show homepage with FAQs
@app.route("/", methods=["GET"])
def home():
    faqs = get_faqs()  # Fetch FAQs
    return render_template("index.html", faqs=faqs, file_uploaded=False)

# File upload route
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]  # Get uploaded file
    try:
        extract_text_from_file(file)  # Extract content from file
        global texts
        # Split the uploaded text into chunks of 500 characters
        texts = [uploaded_text[i:i + 500] for i in range(0, len(uploaded_text), 500)]

        embeddings = model.encode(texts)  # Generate embeddings for chunks
        dimension = embeddings.shape[1]  # Get embedding dimension

        global index
        index = faiss.IndexFlatL2(dimension)  # Create FAISS index
        index.add(np.array(embeddings))  # Add embeddings to index

        faqs = get_faqs()  # Refresh FAQ list
        return render_template("index.html", file_uploaded=True, faqs=faqs)
    except Exception as e:
        # Handle any errors during upload
        return render_template("index.html", file_uploaded=False, error=f"Error: {str(e)}")

# Route to handle user question input
@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]  # Get user question from form
    answer = ""  # Initialize answer

    if question:
        q_emb = model.encode([question])  # Encode the question
        _, I = index.search(np.array(q_emb), k=1)  # Find most relevant text chunk
        context = texts[I[0][0]]  # Get the matching context
        answer = ask_openrouter_api(context, question)  # Get answer from API
        store_question(question, answer, q_emb)  # Save Q&A to DB

    faqs = get_faqs()  # Refresh FAQs
    return render_template("index.html", answer=answer, faqs=faqs, file_uploaded=True)

# Initialize the database when the app starts
init_db()

# Run the app in debug mode
if __name__ == "__main__":
    app.run(debug=True)
