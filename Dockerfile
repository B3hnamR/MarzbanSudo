FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -ms /bin/bash appuser
USER appuser

# App source
COPY --chown=appuser:appuser . .

# Default command
CMD ["python", "-m", "app.main"]
