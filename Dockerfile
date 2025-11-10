# Use an official lightweight Python image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building some Python packages (e.g., asyncmy, psycopg2)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy the dependency file into the container
COPY requirements.txt .

# Install Python dependencies without caching to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into the container
# This copies everything from your local repo root to /app in the container
COPY . .

# --- Set the PYTHONPATH ---
# Add the working directory (/app) to Python's module search path.
# This allows Python (and Uvicorn) to find the 'backend' module
# when trying to import 'backend.app'.
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Expose port 8080 (This is informational; Cloud Run uses the $PORT env var)
EXPOSE 8080

# --- Use $PORT and Shell Form ---
# 1. Use the shell form (a single string) instead of the exec form (JSON array).
#    This is required for the shell to interpret the $PORT environment variable.
# 2. Bind Uvicorn to the $PORT provided by Cloud Run, not a hardcoded '8080'.
# 3. Bind to 0.0.0.0 to accept connections from any IP (required by Cloud Run).
CMD python -m uvicorn backend.app:app --host 0.0.0.0 --port $PORT