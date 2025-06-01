# ---------- Stage 1: Builder ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and DB init + embeddings scripts first
COPY requirements.txt init_db.py generate_embeddings.py ./

# Install all dependencies including sentence-transformers
RUN pip install --upgrade pip && pip install -r requirements.txt

# Create DB and tables before generating embeddings
RUN python init_db.py

# Copy the rest of the app (templates, static, main.py, etc)
COPY . .

# Run embedding generation script
RUN python generate_embeddings.py

# Cleanup heavy packages and caches to keep builder slim
RUN rm -rf /root/.cache /usr/local/lib/python3.10/site-packages/sentence_transformers \
    && find /usr/local -type d -name "sentence_transformers" -exec rm -rf {} + || true


# ---------- Stage 2: Runtime ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy runtime-only requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary files from builder stage
COPY --from=builder /app/faq_db.db ./faq_db.db
COPY --from=builder /app/templates ./templates
COPY --from=builder /app/static ./static
COPY --from=builder /app/main.py ./main.py

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--timeout", "180"]
