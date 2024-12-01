# Use Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies and PostgreSQL client
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
        postgresql-client \
        postgresql \
        postgresql-contrib \
        python3-dev \
        gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install psycopg first
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir psycopg[binary]

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run with uvicorn and reload enabled for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]