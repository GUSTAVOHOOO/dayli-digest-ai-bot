FROM python:3.11-slim

WORKDIR /app

# System dependencies for lxml and Playwright/Crawl4AI
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their system dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium

# Copy source and config
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pytest.ini .

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_DIR=/app/logs
ENV LOG_TO_STDOUT=true

EXPOSE 8080

# Add a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /ms-playwright
USER appuser

# Default command
CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]
