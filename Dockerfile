# OwnVoice — single container serving the API and the site from one origin.
#
# Built for a Hugging Face Docker Space (port 7860, non-root user 1000), but it
# is a plain container and runs anywhere.
#
# Two stages: node builds the React site, python runs it alongside FastAPI. The
# node toolchain never reaches the final image.

# ---------- stage 1: build the frontend ----------
FROM node:20-slim AS web

WORKDIR /build
COPY site/package.json site/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY site/ ./
# .env.production sets VITE_API_BASE="" so the client calls relative paths.
RUN npm run build


# ---------- stage 2: runtime ----------
FROM python:3.11-slim

# libsndfile is required by soundfile for reading uploads and writing the
# simulated WAV; without it every audio endpoint fails at import time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        && rm -rf /var/lib/apt/lists/*

# HF Spaces run as uid 1000. Caches must be writable by that user or model
# downloads fail with a permission error at first request.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /app

# CPU-only torch. The default wheel pulls ~2.5 GB of CUDA libraries that are
# dead weight on a CPU Space and blow past the image size limit.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user backend/ ./backend/
COPY --chown=user src/ ./src/
COPY --chown=user --from=web /build/dist ./backend/web/

USER user

ENV OWNVOICE_HOST=0.0.0.0 \
    OWNVOICE_PORT=7860 \
    OWNVOICE_WEB=/app/backend/web \
    # Point at a model repo on the Hub. Override with a local path if the
    # checkpoint is baked into the image instead.
    OWNVOICE_MODEL=openai/whisper-small \
    # CPU inference on a free Space is slow; keep clips short.
    OWNVOICE_MAX_SECONDS=15

EXPOSE 7860

# Single worker: each one would load its own copy of the models.
CMD ["python", "-m", "uvicorn", "backend.app:app", \
     "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
