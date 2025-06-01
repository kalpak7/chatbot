# ---------- Stage 1: Builder ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build tools for sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Set up DB and generate embeddings
COPY init_db.py generate_embeddings.py ./
RUN python init_db.py

# Copy full app to use data for embeddings
COPY . .
RUN python generate_embeddings.py

# Remove heavy sentence-transformers to reduce image size
RUN rm -rf /root/.cache /usr/local/lib/python3.10/site-packages/sentence_transformers \
    && find /usr/local -type d -name "sentence_transformers" -exec rm -rf {} + || true



# ---------- Stage 2: Runtime ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime deps (pdfplumber needs poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (no sentence-transformers needed now)
COPY requirements.txt ./
RUN pip install --no-cache-dir Flask==3.1.0 requests==2.32.3 pdfplumber==0.11.6 numpy==1.26.4 gunicorn==21.2.0

# Copy runtime files only
COPY --from=builder /app/faq_db.db ./faq_db.db
COPY --from=builder /app/templates ./templates
COPY --from=builder /app/static ./static
COPY --from=builder /app/main.py ./main.py

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--timeout", "180"]
