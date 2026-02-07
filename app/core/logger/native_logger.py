"""
Native Logger Manager
PostgreSQL ve konsol loglama için merkezi yönetim sınıfı
"""
import logging
import sys
from typing import Optional

from app.config import settings


class LoggerManager:
    """
    Native Python logging singleton manager
    Tüm loglama işlemlerini tek bir noktadan yönetir
    """
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        """Singleton pattern implementasyonu"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        Logger instance'ı döndür
        
        Args:
            name: Logger adı (varsayılan: "sb_scrapper")
        
        Returns:
            Configured logger instance
        """
        if cls._logger is None:
            cls._logger = cls._setup_logger(name)
        return cls._logger
    
    @classmethod
    def _setup_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        Logger'ı konfigüre et ve handler'ları ekle
        
        Args:
            name: Logger adı
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name or "sb_scrapper")
        logger.setLevel(getattr(logging, settings.log_level))
        
        # Handler'ları temizle (duplicate önlemek için)
        logger.handlers.clear()
        
        # Console Handler
        if settings.console_logging_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(cls._get_formatter())
            console_handler.setLevel(getattr(logging, settings.log_level))
            logger.addHandler(console_handler)
        
        # PostgreSQL Handler (daha sonra eklenecek)
        if settings.postgres_logging_enabled:
            from app.core.logger.pg_handler import PostgreSQLHandler
            pg_handler = PostgreSQLHandler()
            pg_handler.setFormatter(cls._get_formatter())
            pg_handler.setLevel(getattr(logging, settings.log_level))
            logger.addHandler(pg_handler)
        
        return logger
    
    @classmethod
    def _get_formatter(cls) -> logging.Formatter:
        """
        Log format'ı döndür
        
        Returns:
            Log formatter instance
        """
        return logging.Formatter(settings.log_format)
    
    @classmethod
    def reset_logger(cls) -> None:
        """
        Logger'ı sıfırla (testler için kullanılabilir)
        """
        cls._logger = None


# Global logger instance
logger = LoggerManager.get_logger()
