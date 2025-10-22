# GraphRAG Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for graph processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (if needed for text processing)
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 graphrag && chown -R graphrag:graphrag /app
USER graphrag

# Expose port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8010/api/v1/health/ping')"

# Run the service
CMD ["python", "run.py"]