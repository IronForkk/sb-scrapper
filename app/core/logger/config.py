"""
Logger Konfigürasyonu
Native logger için format ve ayar tanımları
"""
import logging
from typing import Dict, Any

from app.config import settings


# Log format tanımları
LOG_FORMATS: Dict[str, str] = {
    'default': '%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    'simple': '%(levelname)s - %(message)s',
    'detailed': '%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s | %(pathname)s:%(lineno)d',
    'json': '%(message)s',  # JSON format için
}

# Log seviye tanımları
LOG_LEVELS: Dict[str, int] = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}


def get_log_format(format_name: str = 'default') -> str:
    """
    Log format'ı döndür
    
    Args:
        format_name: Format adı (default, simple, detailed, json)
    
    Returns:
        Log format string
    """
    return LOG_FORMATS.get(format_name, LOG_FORMATS['default'])


def get_log_level(level_name: str = None) -> int:
    """
    Log seviyesini döndür
    
    Args:
        level_name: Seviye adı (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Log level integer
    """
    if level_name is None:
        level_name = settings.log_level
    return LOG_LEVELS.get(level_name.upper(), logging.INFO)


def get_formatter(format_name: str = None) -> logging.Formatter:
    """
    Log formatter döndür
    
    Args:
        format_name: Format adı
    
    Returns:
        Logging formatter
    """
    format_str = get_log_format(format_name) if format_name else settings.log_format
    return logging.Formatter(format_str)
