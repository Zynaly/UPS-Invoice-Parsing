# Use a much smaller base image with preinstalled torch CPU
FROM pytorch/pytorch:2.0.1-cpu-py3.10-slim as builder

WORKDIR /app

# Copy requirements first (to cache layers)
COPY requirements.txt .

# Install only what's needed, no cache, no dev packages
RUN pip install --no-cache-dir -r requirements.txt

# Final stage (copy only what’s needed)
FROM python:3.10-slim
WORKDIR /app

# Copy installed Python packages
COPY --from=builder /opt/conda /opt/conda
ENV PATH="/opt/conda/bin:$PATH"

# Copy only your source code (not datasets/models)
COPY . .

CMD ["python", "app.py"]
