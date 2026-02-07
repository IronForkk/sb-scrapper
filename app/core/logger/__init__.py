"""
Logger Modülü
Native Python logging tabanlı logger içerir
"""
from app.core.logger.native_logger import LoggerManager, logger as _logger
from app.core.logger.pg_handler import PostgreSQLHandler
from app.core.logger.gunicorn_interceptor import setup_gunicorn_logging, GunicornLogHandler
from app.core.logger.config import get_log_format, get_log_level, get_formatter
from app.core.logger.postgres_logger import PostgresLogger, postgres_logger

# ========================================
# EXPORTS
# ========================================

# Global logger instance (singleton)
logger = _logger

# Geriye dönük uyumluluk için (eski kodlarda logoru_logger import'u var)
loguru_logger = logger  # Native logger kullanılıyor (loguru artık kullanılmıyor)

__all__ = [
    "LoggerManager",
    "logger",
    "loguru_logger",
    "PostgreSQLHandler",
    "setup_gunicorn_logging",
    "GunicornLogHandler",
    "get_log_format",
    "get_log_level",
    "get_formatter",
    "PostgresLogger",
    "postgres_logger",
]
