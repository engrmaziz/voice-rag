# Use an official Python runtime
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for daphne/channels)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the port (HF defaults to 7860)
EXPOSE 7860

# Command to run the application using Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "7860", "core.asgi:application"]