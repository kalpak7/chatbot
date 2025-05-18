# Use official Python base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code files into container
COPY . .

# Expose port your Flask app listens on
EXPOSE 5000

# Set environment variable so Flask knows to run in production mode
ENV FLASK_ENV=production

# Command to run your Flask app with gunicorn
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
