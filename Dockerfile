FROM python:3.11-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Show Python logs immediately
ENV PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app

# Install basic system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir \
    -r requirements.txt

# Copy project
COPY . .

# Render provides PORT.
EXPOSE 8080

# Start bot
CMD ["python", "bot.py"]
