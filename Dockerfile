"""
Production Docker Configuration for iTow VMS
Enhanced architecture with automated workflows
"""

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    cron \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install production dependencies
RUN pip install --no-cache-dir \
    gunicorn \
    redis \
    celery \
    supervisor

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs \
    /app/static/generated_pdfs \
    /app/data \
    /var/log/supervisor

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///data/vehicles.db

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/api/health || exit 1

# Start supervisor (manages all processes)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
