FROM python:3.11-slim

# Install system dependencies (Tesseract) and clean up apt cache for smaller footprint
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure start script is executable
RUN chmod +x start.sh

# Run application
CMD ["./start.sh"]