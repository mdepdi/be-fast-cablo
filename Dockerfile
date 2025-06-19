FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    libspatialite-dev \
    libsqlite3-mod-spatialite \
    gcc \
    g++ \
    curl \
    # Add PostgreSQL client for database operations
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-database.txt ./
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-database.txt

# Copy application code
COPY ./app /app/app

# Copy alembic configuration and migrations
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Copy data files
COPY ./data /app/data

# Copy entrypoint script
COPY ./docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/outputs /app/data /app/logs \
    && chmod -R 777 /app/uploads /app/outputs /app/logs \
    && chmod -R 755 /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script to run migrations before starting app
ENTRYPOINT ["/app/docker-entrypoint.sh"]