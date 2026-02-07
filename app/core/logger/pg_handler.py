"""
Native PostgreSQL Logging Handler
Native Python logging.Handler sınıfından türetilmiş
Logları doğrudan PostgreSQL tablolarına yazar (senkron)
"""
import logging
from datetime import datetime, timezone
import traceback

from app.db.connection import postgres_connection


class PostgreSQLHandler(logging.Handler):
    """
    Native PostgreSQL logging handler
    
    Logları doğrudan PostgreSQL tablolarına yazar (senkron)
    Hata durumunda exception fırlatır (.clinerules: Tüm loglar PostgreSQL'e saklanmalı)
    """
    
    def __init__(self):
        """Handler'ı başlat"""
        super().__init__()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Log kaydını PostgreSQL'e yaz
        
        Args:
            record: Logging record
        """
        try:
            self._write_log(record)
        except Exception as e:
            # .clinerules: Fallback konsol yazma YASAK, sadece exception fırlat
            raise
    
    def _write_log(self, record: logging.LogRecord) -> None:
        """
        Logu PostgreSQL'e yaz (senkron)
        
        Args:
            record: Logging record
        """
        conn = None
        try:
            conn = postgres_connection.get_connection()
            cursor = conn.cursor()
            
            timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc)
            level = record.levelname
            module = record.name
            function = record.funcName
            line = record.lineno
            message = record.getMessage()
            
            # Stacktrace varsa ekle
            extra_data = None
            if record.exc_info:
                extra_data = ''.join(traceback.format_exception(*record.exc_info))
            
            # Tablo seçimi
            if level in ('ERROR', 'CRITICAL'):
                cursor.execute("""
                    INSERT INTO error_logs (
                        timestamp, level, module, function_name, line_number, 
                        message, stack_trace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (timestamp, level, module, function, line, message, extra_data))
            else:
                cursor.execute("""
                    INSERT INTO application_logs (
                        timestamp, level, module, function_name, line_number, 
                        message, extra_data
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (timestamp, level, module, function, line, message, extra_data))
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
    
    def close(self) -> None:
        """Handler'ı kapat"""
        super().close()
