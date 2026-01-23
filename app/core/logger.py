"""
Loguru ile profesyonel loglama yapılandırması
Renkli konsol logu ve dosya loglama
"""
from loguru import logger
import sys
from pathlib import Path
from app.config import settings

# Log dizinini oluştur
log_dir = Path(settings.log_dir)
log_dir.mkdir(exist_ok=True)

# Varsayılan logger'ı kaldır
logger.remove()

# Konsol logu (renkli)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)

# Info log dosyası
logger.add(
    log_dir / settings.log_info_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="10 MB",
    retention="7 days"
)

# Error log dosyası
logger.add(
    log_dir / settings.log_error_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days"
)

# Logger'ı dışa aktar
__all__ = ["logger"]
