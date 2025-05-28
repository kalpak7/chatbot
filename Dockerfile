# ---------- Stage 1: Builder ----------
FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to install dependencies
COPY requirements.txt .

# Install Python dependencies into a temporary directory
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install runtime system dependencies (no compilers or build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy source code (your `.dockerignore` helps keep this clean)
COPY . .

# Expose port for Flask
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
