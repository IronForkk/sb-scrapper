"""
PostgreSQL Connection Pool Context Manager
Log-Viewer için güvenli bağlantı yönetimi sağlar
"""
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os


# PostgreSQL bağlantı ayarları
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'sb_scrapper')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'sb_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

# PostgreSQL connection pool
postgres_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)


@contextmanager
def get_db_connection():
    """
    Context manager ile güvenli bağlantı yönetimi

    Kullanım:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs")
            results = cursor.fetchall()
    """
    conn = None
    try:
        conn = postgres_pool.getconn()
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            postgres_pool.putconn(conn)


@contextmanager
def get_db_cursor():
    """
    Context manager ile güvenli cursor yönetimi

    Kullanım:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM logs")
            results = cursor.fetchall()
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
        finally:
            cursor.close()


def execute_query(query: str, params: tuple = None, fetch_all: bool = True) -> list:
    """
    PostgreSQL sorgusu çalıştırır (geriye uyumlu)

    Args:
        query: SQL sorgusu
        params: Sorgu parametreleri
        fetch_all: Tüm sonuçları mı getir, yoksa tek mi

    Returns:
        Sonuç listesi
    """
    from datetime import datetime

    try:
        with get_db_cursor() as cursor:
            cursor.execute(query, params or ())

            if fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()

        # Datetime objelerini string'e çevir (JSON serileştirme için)
        if isinstance(result, list):
            for row in result:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
        elif result:
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()

        return result if fetch_all else ([result] if result else [])
    except Exception as e:
        print(f"Query hatası: {e}")
        return []


def get_pool_stats() -> dict:
    """
    Connection pool istatistiklerini döndürür

    Returns:
        Pool istatistikleri sözlüğü
    """
    try:
        return {
            'minconn': postgres_pool.minconn,
            'maxconn': postgres_pool.maxconn,
            'closed': postgres_pool.closed
        }
    except Exception as e:
        return {'error': str(e)}


def close_pool():
    """
    Connection pool'u güvenli şekilde kapatır
    """
    try:
        if postgres_pool and not postgres_pool.closed:
            postgres_pool.closeall()
    except Exception as e:
        print(f"Pool kapatma hatası: {e}")
