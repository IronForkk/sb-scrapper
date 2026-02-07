"""
PostgreSQL Connection Yönetimi (Senkron)
Sadece senkron bağlantı - async/await YASAK
Tek istek modu için doğrudan bağlantı - connection pool YASAK
"""
import psycopg2
from app.config import settings


def _get_logger():
    """Lazy import logger to avoid circular import"""
    from app.core.logger.native_logger import logger
    return logger


class PostgresConnection:
    """
    Senkron PostgreSQL bağlantısı
    Strict mode: PostgreSQL yoksa uygulama çalışmaz
    Tek istek modu için doğrudan bağlantı kullanılır
    """
    def __init__(self):
        self._connection = None
    
    def initialize(self):
        """Bağlantı başarısız olursa exception fırlatır (strict mode)"""
        try:
            self._connection = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db
            )
            # Test connection
            cursor = self._connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            _get_logger().info("PostgreSQL bağlantısı başarılı")
        except Exception as e:
            raise RuntimeError(
                f"PostgreSQL bağlantı hatası (strict mode): {e}. "
                f"Uygulama verisi kaybını önlemek için başlatılmıyor."
            )
    
    def get_connection(self):
        """Bağlantı al"""
        if self._connection is None or self._connection.closed:
            self.initialize()
        return self._connection
    
    def close(self):
        """Bağlantıyı kapat"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            _get_logger().info("PostgreSQL bağlantısı kapatıldı.")


# Singleton instance
postgres_connection = PostgresConnection()
