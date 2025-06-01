# ---------- Stage 1: Builder ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy files needed to generate embeddings
COPY requirements.txt generate_embeddings.py ./  # requirements.txt includes sentence-transformers
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy entire app to builder stage (for access to DB and text files)
COPY . .

# Generate the database with precomputed embeddings
RUN python generate_embeddings.py

# 🧽 CLEANUP STEP: Remove model files and sentence-transformers package
RUN rm -rf /root/.cache /usr/local/lib/python3.10/site-packages/sentence_transformers \
    && find /usr/local -type d -name "sentence_transformers" -exec rm -rf {} + || true


# ---------- Stage 2: Runtime ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed to run the Flask app
COPY requirements_runtime.txt .
RUN pip install --no-cache-dir -r requirements_runtime.txt

# Copy source code and the generated DB from builder
COPY --from=builder /app /app

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--timeout", "180"]
