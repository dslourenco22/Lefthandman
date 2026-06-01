FROM python:3.11-slim

# System deps: build tools for some wheels, plus libs PyMuPDF/pdfplumber may need
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy model and warm the sentence-transformers cache at build time
# so the first request isn't paying the download cost.
RUN python -m spacy download en_core_web_sm
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000

# Single worker by default. For 500+ resume batches in production, run multiple
# workers and move process_batch onto a real queue (see README).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
