"""
PostgreSQL Veritabanı Modülü
"""
from app.db.connection import connection_pool

__all__ = ["connection_pool"]
