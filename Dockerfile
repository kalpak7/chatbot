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

# Copy rest of the app and generate embeddings
COPY . ./ 
RUN python generate_embeddings.py


# ---------- Stage 2: Runtime ----------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only required system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    pkg-config \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies exactly from requirements (including sentence-transformers)
COPY requirements.txt ./ 
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files from builder
COPY --from=builder /app/faq_db.db ./faq_db.db
COPY --from=builder /app/templates ./templates
COPY --from=builder /app/static ./static
COPY --from=builder /app/main.py ./main.py
COPY --from=builder /app/init_db.py ./init_db.py
COPY --from=builder /app/generate_embeddings.py ./generate_embeddings.py

EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--timeout", "180"]
