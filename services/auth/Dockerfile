FROM python:3.12-slim

WORKDIR /app

# Install runtime and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/auth/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/auth/src /app/services/auth/src

ENV PYTHONPATH=/app \
    PORT=8001 \
    HOST=0.0.0.0

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Create non-root user for security hardening
RUN groupadd -r appsec && useradd -r -g appsec -d /app -s /sbin/nologin -c "AppSec Service User" appsec && \
    chown -R appsec:appsec /app

USER appsec

CMD ["uvicorn", "services.auth.src.main:app", "--host", "0.0.0.0", "--port", "8001"]
