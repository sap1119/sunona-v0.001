FROM python:3.10.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 \
    git \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    gcc \
    g++ \
    python3-dev \
    espeak \
    libespeak-dev \
    build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel





# Install torch and torchaudio first (required dependencies)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch~=2.0.0 torchaudio~=2.0.0 --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install dependencies
COPY local_setup/dockerfiles/requirements_minimal.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt || \
    (echo "Failed to install requirements. See error above." && exit 1)

# Copy sunona package
COPY sunona /app/sunona

# Set PYTHONPATH so Python can find the sunona module
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy application files
COPY local_setup/quickstart_server.py /app/
COPY local_setup/presets /app/presets

EXPOSE 5001

CMD ["uvicorn", "quickstart_server:app", "--host", "0.0.0.0", "--port", "5001"]
