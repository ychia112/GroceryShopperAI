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

# Copy all application files into the container (from your local backend directory)
COPY . .

# Expose port 8080 (Cloud Run listens on this port by default)
EXPOSE 8080

# Command to run the FastAPI app with Uvicorn
# Format: uvicorn <module_name>:<app_instance> --host 0.0.0.0 --port 8080
# Example: If your FastAPI instance is "app" inside backend/app.py, then use "backend.app:app"
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]