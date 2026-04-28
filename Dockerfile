# --------------------------
# Backend Dockerfile
# --------------------------
FROM python:3.13-slim AS builder
WORKDIR /app

# Install build tools & dependencies
RUN apt-get update && apt-get install -y gcc git && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
