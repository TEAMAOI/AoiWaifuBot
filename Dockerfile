FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Install git, ffmpeg and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip3 install --upgrade pip setuptools

# Copy application code
COPY . /app/

# Set working directory
WORKDIR /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -U -r requirements.txt

# Run the bot
CMD ["python3", "-m", "aoiwaifu"]
