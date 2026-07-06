FROM python:3.11-slim

WORKDIR /app

# System deps: poppler (pdf2image), libreoffice (unstructured docx),
# tesseract (OCR), libpq-dev + gcc (asyncpg build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libreoffice-writer \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Default env (uses HuggingFace free inference)
RUN if [ ! -f .env ]; then cp .env.example .env; fi

EXPOSE 7860

CMD sh start.sh
