# Python Alpine tabanlı hafif imaj
FROM python:3.11-alpine

# Work directory
WORKDIR /app

# Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Sistem bağımlılıkları
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Port expose
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

# Uygulamayı başlat
CMD ["python", "app.py"]
