"""
SB-Scraper Özel Exception Sınıfı
"""
from typing import Dict, Any


class SBScraperError(Exception):
    """
    SB-Scraper özel exception sınıfı
    Error code'ları ile detaylı hata mesajları
    """
    def __init__(self, error_code: str, message: str, details: Any = None):
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Hata bilgilerini sözlüğe çevir"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }
