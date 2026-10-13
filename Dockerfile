FROM python:3.11-slim

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for uploads and database
RUN mkdir -p /app/uploads /app/data

# Make sure the app is accessible
EXPOSE 5000

ENV FLASK_ENV=production
ENV DATABASE_PATH=/app/data/allergylens.db
ENV UPLOAD_FOLDER=/app/uploads
ENV TESSERACT_CMD=/usr/bin/tesseract

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
