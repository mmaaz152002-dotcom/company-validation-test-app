FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DATABASE_PATH=/app/data/leads.db \
    LOG_FILE=/app/logs/app.log

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /app appuser

COPY pyproject.toml README.md ./
COPY app ./app
COPY data/*.csv ./data/

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=3)" || exit 1

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
