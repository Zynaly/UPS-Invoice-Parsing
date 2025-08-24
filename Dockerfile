# Use a minimal Python base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (only what’s needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install minimal dependencies (CPU-only Torch + Transformers)
RUN pip install --upgrade pip \
 && pip install --no-cache-dir torch==2.0.1+cpu torchvision==0.15.2+cpu \
        -f https://download.pytorch.org/whl/cpu/torch_stable.html \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose app port
EXPOSE 5000

# Run your app (change if not Flask)
CMD ["python", "app.py"]
