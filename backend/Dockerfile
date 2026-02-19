FROM python:3.11-slim

# Install system dependencies required by pysam and htslib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies (including pysam which builds on Linux)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pysam==0.22.0

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
