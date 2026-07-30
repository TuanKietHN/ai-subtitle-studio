FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    QT_QPA_PLATFORM=offscreen \
    AI_SUBTITLE_MODEL_CACHE=/app/model-cache \
    AI_SUBTITLE_OUTPUT_DIR=/app/outputs \
    AI_SUBTITLE_DATA_DIR=/app/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        build-essential \
        libsndfile1 \
        libgl1 \
        libegl1 \
        libglib2.0-0 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY resources ./resources
COPY src ./src
COPY tests ./tests
COPY specs ./specs
COPY packaging ./packaging

RUN python -m pip install --upgrade pip \
    && pip install "torch~=2.8.0" "torchvision~=0.23.0" "torchaudio~=2.8.0" --index-url https://download.pytorch.org/whl/cu128 \
    && pip install -e .[dev]

RUN mkdir -p /app/model-cache /app/outputs /app/data

CMD ["python", "-m", "ai_subtitle_studio.app"]
