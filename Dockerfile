# Use official Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

# Set environment variable
ENV FLASK_ENV=production

# Start app with gunicorn
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
