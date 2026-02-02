"""
Loguru ile PostgreSQL loglama
Tüm loglar PostgreSQL tablolarında saklanır

Structured Logging (JSON format) opsiyonel olarak etkinleştirilebilir.
"""
from loguru import logger
import sys
from app.config import settings
from app.core.postgres_logger import postgres_handler

# Varsayılan logger'ı kaldır
logger.remove()

# ========================================
# 1. Konsol Logu (Opsiyonel - Debug için)
# ========================================
if settings.console_logging_enabled:
    # Structured logging etkinse JSON format, değilse insan okunabilir format
    if settings.structured_logging_enabled:
        logger.add(
            sys.stdout,
            format="{message}",
            level=settings.log_level,
            colorize=False,
            serialize=True,  # JSON format
            backtrace=False,
            diagnose=False
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
            backtrace=False,
            diagnose=False
        )

# ========================================
# 2. PostgreSQL Log Handler (TEK LOG KAYNAĞI)
# ========================================
if settings.postgres_logging_enabled:
    # Structured logging etkinse JSON format, değilse insan okunabilir format
    if settings.structured_logging_enabled:
        logger.add(
            postgres_handler,
            format="{message}",
            level=settings.log_level,
            serialize=True,  # JSON format
            backtrace=False,
            diagnose=False
        )
    else:
        logger.add(
            postgres_handler,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.log_level,
            backtrace=False,
            diagnose=False
        )

# Logger'ı dışa aktar
__all__ = ["logger"]
