"""
Hata Yönetimi Modülü
Exceptions ve Error codes içerir
"""
from app.errors.exceptions import SBScraperError
from app.errors.error_codes import ErrorCode

__all__ = ["SBScraperError", "ErrorCode"]
