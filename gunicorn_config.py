"""
Gunicorn Konfigürasyon Dosyası
SB-Scrapper için Gunicorn ayarları
"""
import sys
import os

# ============================================
# WORKER AYARLARI
# ============================================

# Worker sayısı - Tek istek modu için 1 worker
# .clinerules kuralı: API sadece tek bir isteği kabul etmeli
workers = 1

# Worker sınıfı - Uvicorn worker kullanımı (FastAPI için gerekli)
# Uvicorn worker, FastAPI'nin ASGI interface'ini doğru kullanır
worker_class = "uvicorn.workers.UvicornWorker"

# Worker başına maksimum bağlantı sayısı
worker_connections = 1000

# Maksimum istek sayısı (worker restart için)
max_requests = 1000

# Maksimum istek sayısı jitter (rastgelelik)
max_requests_jitter = 50

# Timeout ayarı (saniye)
timeout = 120

# Keepalive süresi (saniye)
keepalive = 5

# ============================================
# BIND AYARI
# ============================================

# Bind adresi (0.0.0.0:PORT)
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# ============================================
# LOG AYARLARI
# ============================================

# Access log (stdout)
accesslog = "-"

# Error log (stderr)
errorlog = "-"

# Log seviyesi
loglevel = os.getenv("LOG_LEVEL", "info")

# ============================================
# GUNICORN LOG INTERCEPTOR
# ============================================

# Gunicorn log interceptor'ı yükle
# Bu, Gunicorn loglarını PostgreSQL'e yönlendirir
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from app.core.logger.gunicorn_interceptor import setup_gunicorn_logging
    setup_gunicorn_logging()
except Exception as e:
    # Hata durumunda konsola yaz (logger henüz hazır değil)
    print(f"[WARNING] Gunicorn log interceptor yüklenemedi: {e}")
    print("[WARNING] Gunicorn logları sadece konsola yazılacak")

# ============================================
# DİĞER AYARLAR
# ============================================

# Preload app (opsiyonel - memory kullanımını artırabilir)
preload_app = False

# Graceful timeout (saniye)
graceful_timeout = 30

# Worker timeout (saniye)
worker_timeout = 120

# Worker boot timeout (saniye)
worker_boot_timeout = 60
