"""
Gunicorn Log Interceptor
Gunicorn access ve error loglarını yakalayıp PostgreSQL'e yazar
"""
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.db.connection import postgres_connection


class GunicornLogHandler(logging.Handler):
    """
    Gunicorn logları için PostgreSQL handler
    
    Gunicorn access ve error loglarını `gunicorn_logs` tablosuna yazar
    """
    
    def __init__(self):
        """Handler'ı başlat"""
        super().__init__()
        self._fallback_enabled = True
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Gunicorn log kaydını PostgreSQL'e yaz
        
        Args:
            record: Logging record
        """
        try:
            self._write_log(record)
        except Exception as e:
            # Fallback: konsola yaz
            if self._fallback_enabled:
                print(f"[GunicornHandler ERROR] {self.format(record)}")
                print(f"[GunicornHandler ERROR] {e}")
    
    def _write_log(self, record: logging.LogRecord) -> None:
        """
        Gunicorn logunu PostgreSQL'e yaz (senkron)
        
        Args:
            record: Logging record
        """
        conn = None
        try:
            conn = postgres_connection.get_connection()
            cursor = conn.cursor()
            
            timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc)
            level = record.levelname
            message = self.format(record)
            
            # Worker ID'yi record'dan al (varsa)
            worker_id = getattr(record, 'worker_id', None) or 'unknown'
            
            # Extra data (varsa)
            extra_data = None
            if record.exc_info:
                import traceback
                extra_data = ''.join(traceback.format_exception(*record.exc_info))
            
            cursor.execute("""
                INSERT INTO gunicorn_logs (
                    timestamp, level, worker_id, message, extra_data
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (timestamp, level, worker_id, message, extra_data))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()


def setup_gunicorn_logging() -> None:
    """
    Gunicorn loglama sistemini kur
    
    Bu fonksiyon gunicorn_config.py'den çağrılır
    Gunicorn access ve error loglarını PostgreSQL'e yönlendirir
    """
    if not settings.gunicorn_logging_enabled:
        return
    
    # Gunicorn logger'larını al
    gunicorn_logger = logging.getLogger('gunicorn')
    gunicorn_access_logger = logging.getLogger('gunicorn.access')
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    
    # Handler oluştur
    gunicorn_handler = GunicornLogHandler()
    gunicorn_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s - %(message)s'
    ))
    
    # Handler'ları ekle
    gunicorn_logger.addHandler(gunicorn_handler)
    gunicorn_access_logger.addHandler(gunicorn_handler)
    gunicorn_error_logger.addHandler(gunicorn_handler)
    
    # Log seviyesini ayarla
    gunicorn_logger.setLevel(getattr(logging, settings.log_level))
    gunicorn_access_logger.setLevel(getattr(logging, settings.log_level))
    gunicorn_error_logger.setLevel(getattr(logging, settings.log_level))


def intercept_gunicorn_output() -> None:
    """
    Gunicorn stdout/stderr çıktısını yakala ve PostgreSQL'e yaz
    
    Bu fonksiyon Gunicorn'un doğrudan stdout/stderr çıktılarını
    yakalamak için kullanılır (opsiyonel)
    """
    # Bu fonksiyon ileride eklenebilir
    # Şu an için Gunicorn'un kendi logging sistemi kullanılıyor
    pass
