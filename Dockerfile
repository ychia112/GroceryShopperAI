# Use an official lightweight Python image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building some Python packages (e.g., asyncmy, psycopg2)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 1. Copy ONLY requirements.txt at repo root
# ---------------------------------------------------------
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---------------------------------------------------------
# 2. Copy ONLY backend/ directory into /app/backend
# ---------------------------------------------------------
COPY backend /app/backend

# Set the working directory to your backend folder
WORKDIR /app/backend

# Expose port 8080 (This is informational; Cloud Run uses the $PORT env var)
EXPOSE 8080

# --- Use $PORT and Shell Form ---
# 1. Use the shell form (a single string) instead of the exec form (JSON array).
#    This is required for the shell to interpret the $PORT environment variable.
# 2. Bind Uvicorn to the $PORT provided by Cloud Run, not a hardcoded '8080'.
# 3. Bind to 0.0.0.0 to accept connections from any IP (required by Cloud Run).
CMD exec uvicorn app:app --host 0.0.0.0 --port $PORT