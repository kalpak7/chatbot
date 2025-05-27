Error Debugger Chatbot with Groq Ai

Description:
A Flask web app that accepts .pdf or .txt files, extracts and chunks text, encodes it using SentenceTransformers, and queries the Groq LLaMA 3 (70B or 8B) API to generate FAQs or answer user questions.


Features:

Upload PDF/TXT files

Auto-generate FAQs using LLaMA 3

Ask questions based on uploaded document

Uses FAISS for fast semantic retrieval

Dockerized and CI-enabled (GitHub Actions)

Telegram CI notifications



Requirements:

Python 3.10+

Groq API Key (free at https://console.groq.com/keys)




Setup (Local)

1. Clone the repository

git clone https://github.com/your-username/your-repo.git
cd your-repo


2. Install dependencies

pip install -r requirements.txt


3. Add your Groq API key
Create a .env file:

GROQ_API_KEY=your_api_key_here


4. Run the app

python main.py


5. Visit
http://127.0.0.1:5000/






Run with Docker

1. Build Docker image:

docker build -t error-debugger-chatbot .


2. Run the container:

docker run -e GROQ_API_KEY=your_api_key_here -p 5000:5000 error-debugger-chatbot





CI/CD Notes

CI tests all sample files with app_test.py

Docker image built & pushed to GitHub Container Registry

Telegram alert after CI pipeline passes
