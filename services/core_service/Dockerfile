FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies
COPY requirements.txt .
COPY services/core_service/requirements.txt ./services/core_service/requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r services/core_service/requirements.txt \
    && apt-get purge -y --auto-remove gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy shared and service code
COPY shared/ ./shared/
COPY services/core_service/ ./services/core_service/

# 4. Set Python path and run
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.core_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
