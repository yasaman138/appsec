FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies and security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt /app/requirements.txt
COPY requirements.txt /app/root-requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio

COPY services /app/services
COPY tests /app/tests
COPY pyproject.toml /app/pyproject.toml

ENV PYTHONPATH=/app \
    PORT=8002 \
    HOST=0.0.0.0

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Create non-root user for security hardening
RUN groupadd -r appsec && useradd -r -g appsec -d /app -s /sbin/nologin -c "AppSec Service User" appsec && \
    chown -R appsec:appsec /app

USER appsec

CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8002"]
