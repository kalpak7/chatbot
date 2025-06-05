🧠 Error Debugger Chatbot

A Flask-based chatbot that uses LLaMA models via Groq API to help debug and answer queries from uploaded PDF documents or text. It supports intelligent FAQ generation, semantic search using FAISS, and auto-deployment with Docker and CI/CD pipelines.

---

🚀 Features

- Upload PDF or text files to interact with AI
- Embedding-based semantic search using sentence-transformers + FAISS
- FAQ auto-generation from frequent answers
- Uses Groq-hosted LLaMA models for response generation
- Dockerized for portable deployment
- CI/CD with GitHub Actions
- Telegram notifications on every successful build

---

🛠️ Setup Instructions

🔧 Local Development

1. Clone the repository:
   git clone https://github.com/<your-username>/error-debugger-chatbot.git
   cd error-debugger-chatbot

2. Install dependencies:
   pip install -r requirements.txt

3. Run the app:
   export GROQ_API_KEY=your_api_key_here  # or set in .env file
   python main.py

4. Run tests:
   python -m unittest discover -s test

---

🐳 Docker Deployment

🔨 Build Docker image locally

docker build -t error-debugger-chatbot .

▶️ Run Docker container

docker run -e GROQ_API_KEY=your_api_key_here -p 5000:5000 error-debugger-chatbot

---

📦 GitHub Container Registry (GHCR)

⬇️ Pull the image

docker pull ghcr.io/<your-username>/error-debugger-chatbot:latest

▶️ Run it

docker run -e GROQ_API_KEY=your_api_key_here -p 5000:5000 ghcr.io/<your-username>/error-debugger-chatbot:latest

---

🔁 CI/CD Workflow

This repo uses GitHub Actions for:

- Automated testing on push/pull to main
- Docker image build & push to GHCR
- Telegram notification on success

💬 Example Telegram Notification

✅ CI Passed on `main`
👤 By: `username`
📝 Commit Message: `Fix: added error handling to PDF upload`
🐳 Docker Image Built & Pushed!
📦 ghcr.io/<your-username>/error-debugger-chatbot:latest

---

🔐 Secrets Required (in GitHub repo)

- GROQ_API_KEY – Your Groq API key
- CR_PAT – GitHub Container Registry token (can be a personal access token with write:packages scope)
- TELEGRAM_BOT_TOKEN – Bot token from @BotFather
- TELEGRAM_CHAT_ID – Your chat/group ID to receive CI notifications

---

📁 Project Structure

.
├── main.py                 # Flask app logic
├── templates/              # HTML templates
├── static/                 # CSS/JS files
├── test/
│   └── app_test.py         # Unit tests
├── Dockerfile              # Multi-stage Docker build
├── requirements.txt        # Python dependencies
└── .github/workflows/
    └── ci.yml              # CI pipeline config

---

🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Push your changes and open a PR to main

---

📝 License

This project is licensed under the MIT License.
