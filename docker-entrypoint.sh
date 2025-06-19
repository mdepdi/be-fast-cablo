#!/bin/bash
set -e

echo "Starting Fast LastMile API container..."

# Fix volume permissions at runtime
echo "Fixing volume permissions..."
chmod -R 777 /app/uploads /app/outputs /app/logs 2>/dev/null || true

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Checking connection to external database..."

    # Extract database connection details from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASSWORD="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"

        # Set PostgreSQL password for pg_isready
        export PGPASSWORD=$DB_PASSWORD

        # Try to connect with timeout and retries
        MAX_RETRIES=30
        RETRY_COUNT=0

        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t 5; then
                echo "External database is ready!"
                break
            else
                RETRY_COUNT=$((RETRY_COUNT + 1))
                echo "Database connection attempt $RETRY_COUNT/$MAX_RETRIES failed. Retrying in 2 seconds..."
                sleep 2
            fi
        done

        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "ERROR: Could not connect to external database after $MAX_RETRIES attempts"
            echo "Please check your DATABASE_URL and ensure the database is accessible"
            exit 1
        fi

        # Unset password for security
        unset PGPASSWORD
    else
        echo "WARNING: Could not parse DATABASE_URL. Skipping database check."
    fi
fi

# Run database migrations
echo "Running database migrations..."
if alembic upgrade head; then
    echo "Database migrations completed successfully!"
else
    echo "WARNING: Database migrations failed. This might be normal if migrations are already up to date."
    echo "Continuing with application startup..."
fi

# Start the FastAPI application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000