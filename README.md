=========================================================
            Error Debugger Chatbot with Groq AI
=========================================================

Description:
------------
A Flask web app that accepts `.pdf` or `.txt` files, extracts the text,
and queries the Groq LLaMA 3 (70B or 8B) API to generate FAQs or 
answer user questions based on the uploaded content.

---------------------------------------------------------

Features:
---------
- Upload PDF/TXT files
- Auto-generate FAQs using LLaMA 3
- Ask questions based on uploaded document
- Dockerized and CI-enabled (GitHub Actions)
- Telegram CI notifications

---------------------------------------------------------

Requirements:
-------------
- Python 3.10+
- Groq API Key (free at https://console.groq.com/keys)

---------------------------------------------------------

Setup (Local):
--------------
1. Clone the repository:
   > git clone https://github.com/your-username/your-repo.git  
   > cd your-repo

2. Install dependencies:
   > pip install -r requirements.txt

3. Add your Groq API key:  
   Create a `.env` file in the root directory with the following content:
   > GROQ_API_KEY=your_api_key_here

4. Run the Flask app:
   > python main.py

5. Open in browser:  
   > http://127.0.0.1:5000/

---------------------------------------------------------

Run with Docker:
----------------
1. Build Docker image:
   > docker build -t error-debugger-chatbot .

2. Run the container:
   > docker run -e GROQ_API_KEY=your_api_key_here -p 5000:5000 error-debugger-chatbot

---------------------------------------------------------

CI/CD Notes:
------------
- Automatically tests all sample input files via `app_test.py`
- Builds and pushes Docker image to GitHub Container Registry
- Sends Telegram alert after successful CI pipeline

---------------------------------------------------------

Credits:
--------
- Powered by Groq (https://console.groq.com/)
- PDF parsing via pdfplumber
- Web framework: Flask
