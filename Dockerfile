# MatchPoint: one container serving the React app and the FastAPI backend.
#
#   docker build -t matchpoint .
#   docker run -p 8000:8000 -v matchpoint-data:/data matchpoint
#
# Build without the AI embedding model (smaller image, ~150 MB RAM, TF-IDF matching):
#   docker build --build-arg WITH_EMBEDDINGS=false -t matchpoint .

# ---------- 1. build the React frontend
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 2. Python runtime
FROM python:3.12-slim
ARG WITH_EMBEDDINGS=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    DATA_DIR=/data \
    HF_HOME=/app/models \
    PORT=8000

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-embeddings.txt ./
RUN pip install -r requirements.txt \
 && if [ "$WITH_EMBEDDINGS" = "true" ]; then \
        pip install torch --index-url https://download.pytorch.org/whl/cpu \
     && pip install -r requirements-embeddings.txt \
     && python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2')"; \
    fi

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/sample_resumes ./sample_resumes
COPY --from=web /web/dist /app/frontend/dist

# run as an unprivileged user; /data holds the database, uploaded resumes and the session key
RUN useradd --create-home --uid 10001 matchpoint \
 && mkdir -p /data /app/models \
 && chown -R matchpoint:matchpoint /data /app/models
USER matchpoint
# the model is baked into the image: never download at runtime
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=4)"

# --proxy-headers + --forwarded-allow-ips: trust the hosting platform's HTTPS proxy so the
# app knows requests were HTTPS (secure cookies, HSTS). PORT is set by most hosts.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
