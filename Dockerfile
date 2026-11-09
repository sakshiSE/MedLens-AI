
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TESSERACT_CMD=/usr/bin/tesseract

WORKDIR /app

# Install Tesseract and the library required by FAISS
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r backend/requirements.txt

# Copy backend application
COPY backend ./backend

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
