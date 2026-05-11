FROM python:3.11-slim

WORKDIR /app

# System dependencies for lxml and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and config
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_DIR=/app/logs
ENV LOG_TO_STDOUT=true

# Add a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]
