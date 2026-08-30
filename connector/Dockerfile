FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY connector ./connector

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD test -f /tmp/connector_healthy || exit 1

CMD ["python", "-m", "connector.main"]