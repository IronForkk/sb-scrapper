# ==========================================
# Stage 1: Temel Kurulumlar
# ==========================================
FROM ubuntu:22.04 AS base
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Locale Configuration (Türkçe Ayarları)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata locales && \
    sed -i '/tr_TR.UTF-8/s/^# //g' /etc/locale.gen && locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV TZ=Turkey/Istanbul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ENV LANG=tr_TR.UTF-8 LANGUAGE=tr_TR:en LC_ALL=tr_TR.UTF-8

# Install Common Fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation fonts-liberation2 fonts-font-awesome \
    fonts-ubuntu fonts-terminus fonts-powerline fonts-open-sans \
    fonts-mononoki fonts-roboto fonts-lato && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Linux Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 \
    libnss3 libu2f-udev libvulkan1 libwayland-client0 \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Utilities & Bash Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    xdg-utils ca-certificates curl sudo unzip wget xvfb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm ./google-chrome-stable_current_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-setuptools python3-dev python3-tk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ==========================================
# Stage 2: Python Dependencies
# ==========================================
FROM base AS python-deps
WORKDIR /app

# Upgrade pip ve wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# SeleniumBase ve diğer bağımlılıkları kur
RUN pip install --no-cache-dir seleniumbase pyautogui

# Chromedriver indir
RUN seleniumbase get chromedriver --path

# ==========================================
# Stage 3: Final Stage
# ==========================================
FROM python-deps AS final
WORKDIR /app

# Önce requirements.txt kopyala ve kur (cache layer optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY app ./app

# Static dosyalarını kopyala
COPY static ./static

# Black-list dosyasını kopyala
COPY black-list.lst .

# Log dizinini oluştur
RUN mkdir -p /app/logs

# API Portunu dışarı aç
EXPOSE 8000

# Environment variables
ENV HEADLESS=true
ENV WAIT_TIME=8
ENV LOG_LEVEL=INFO

# Konteyner başladığında API'yi çalıştır
# CMD ["python3", "-m", "app.main"]
CMD ["gunicorn", "app.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--max-requests", "1000", "--max-requests-jitter", "50", "--timeout", "300"]
