"""
PostgreSQL Connection Pool Yönetimi
FastAPI (asyncpg) için async connection pool

CPU bazlı optimizasyon:
- min_size: CPU çekirdeği sayısının yarısı
- max_size: CPU çekirdeği sayısı
"""
import asyncio
import os
import asyncpg
from app.config import settings


def _calculate_pool_size() -> tuple[int, int]:
    """
    CPU çekirdeği sayısına göre pool boyutunu hesaplar
    
    Returns:
        (min_size, max_size)
    """
    try:
        cpu_count = os.cpu_count() or 4
        min_size = max(1, cpu_count // 2)
        max_size = max(min_size * 2, cpu_count)
        return min_size, max_size
    except Exception:
        # Hata durumunda varsayılan değerler
        return 5, 10


class StrictConnectionPool:
    """
    Strict mode connection pool
    PostgreSQL bağlantısı başarısız olursa exception fırlatır
    """
    def __init__(self):
        self._pool = None
    
    async def initialize(self):
        """Bağlantı başarısız olursa exception fırlatır (strict mode)"""
        # CPU bazlı pool boyutunu hesapla
        calculated_min, calculated_max = _calculate_pool_size()
        
        # Config'den gelen değerleri kullan, ancak CPU bazlı optimize et
        min_size = max(calculated_min, settings.postgres_pool_size // 2)
        max_size = max(calculated_max, settings.postgres_pool_size + settings.postgres_max_overflow)
        
        for attempt in range(settings.postgres_max_retries):
            try:
                self._pool = await asyncpg.create_pool(
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                    database=settings.postgres_db,
                    min_size=min_size,
                    max_size=max_size,
                    command_timeout=30
                )
                # Test connection
                async with self._pool.acquire() as conn:
                    await conn.fetchval('SELECT 1')
                print(f"✅ PostgreSQL bağlantısı başarılı. Pool: min={min_size}, max={max_size}, CPU={os.cpu_count() or 4}")
                return
            except Exception as e:
                if attempt == settings.postgres_max_retries - 1:
                    raise RuntimeError(
                        f"PostgreSQL bağlantı hatası (strict mode): {e}. "
                        f"Uygulama verisi kaybını önlemek için başlatılmıyor."
                    )
                print(f"⚠️ PostgreSQL bağlantı denemesi {attempt + 1}/{settings.postgres_max_retries} başarısız...")
                await asyncio.sleep(5)
    
    async def get_pool(self):
        """Pool'u döndür"""
        if self._pool is None:
            await self.initialize()
        return self._pool
    
    async def close(self):
        """Pool'u kapat"""
        if self._pool:
            await self._pool.close()
            print("🔌 PostgreSQL bağlantısı kapatıldı.")
 

# Singleton instance
connection_pool = StrictConnectionPool()
