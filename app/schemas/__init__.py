"""
Pydantic Şemaları Modülü
Request ve Response şemaları içerir
"""
from app.schemas.request import ScrapeRequest
from app.schemas.response import ScrapeResponse

__all__ = ["ScrapeRequest", "ScrapeResponse"]
