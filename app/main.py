"""
FastAPI Ana Uygulaması
SB-Scraper API endpoint'leri
"""
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib
import time
import threading
from fastapi import FastAPI, HTTPException, APIRouter, Request, Response, Header, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import ScrapeRequest, ScrapeResponse
from app.core.browser import BrowserManager
from app.core.logger import logger
from app.core.postgres_logger import postgres_logger
from app.middleware.request_tracker import request_tracker_middleware
from app.swagger_config import custom_openapi
from app.tasks import task_queue
from app.utils.memory_monitor import get_memory_monitor
from app.utils.monitor import get_system_monitor

# Rate Limiting (Opsiyonel - slowapi gerekli)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False


# ==================== CUSTOM ERROR CLASS ====================
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


# Error Code Tanımları
class ErrorCode:
    """Error code sabitleri"""
    # Tarayıcı Hataları
    BROWSER_BUSY = "BROWSER_BUSY"
    BROWSER_INIT_FAILED = "BROWSER_INIT_FAILED"
    BROWSER_CRASHED = "BROWSER_CRASHED"
    
    # PostgreSQL Hataları
    POSTGRES_CONNECTION_FAILED = "POSTGRES_CONNECTION_FAILED"
    POSTGRES_QUERY_FAILED = "POSTGRES_QUERY_FAILED"
    
    # Validasyon Hataları
    INVALID_URL = "INVALID_URL"
    BLACKLISTED_DOMAIN = "BLACKLISTED_DOMAIN"
    AUTH_FAILED = "AUTH_FAILED"
    
    # Rate Limiting Hataları
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


# ==================== AUTHENTICATION DEPENDENCY ====================
async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """
    API key doğrulama (opsiyonel)
    
    Args:
        x_api_key: X-API-Key header değeri
    
    Raises:
        HTTPException: Authentication başarısız olursa
    """
    if settings.auth_enabled:
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key gerekli. X-API-Key header'ı sağlayın.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        if x_api_key != settings.auth_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Geçersiz API key"
            )


# ==================== TAGS METADATA ====================
tags_metadata = [
    {
        "name": "Genel",
        "description": "API durum ve sağlık kontrolü endpoint'leri"
    },
    {
        "name": "Scraping",
        "description": "Web scraping ve analiz işlemleri"
    },
    {
        "name": "Loglar",
        "description": "PostgreSQL log görüntüleme endpoint'leri"
    },
    {
        "name": "Görevler",
        "description": "Async task queue yönetimi endpoint'leri"
    }
]


# ==================== CONTACT VE LICENSE BİLGİLERİ ====================
contact_info = {
    "name": "SB-Scraper Team",
    "email": "support@example.com",
    "url": "https://github.com/example/sb-scrapper"
}

license_info = {
    "name": "MIT License",
    "url": "https://opensource.org/licenses/MIT"
}


# ==================== RATE LIMITING (Opsiyonel) ====================
if settings.rate_limiting_enabled and RATE_LIMITING_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI(
        title="SB-Scraper API",
        description="""
        SB-Scraper, SeleniumBase tabanlı gelişmiş web scraping API'sidir.
        
        ## Özellikler:
        
        * **Çoklu Tarama Modu:** Ham URL ve ana domain taraması
        * **Mobil Görünüm:** Mobil cihaz ekran görüntüleri
        * **Arama Motoru Entegrasyonu:** Google ve DuckDuckGo sonuçları
        * **HTML Kaynak Kodu:** Sayfa kaynak kodlarını alma
        * **Black-list Koruması:** İstenmeyen domain'leri filtreleme
        * **Anti-Detection:** WebDriver tespitini önleme
        * **Rate Limiting:** İstek sınırlama (opsiyonel)
        
        ## Kullanım:
        
        1. Taranacak URL'i belirtin
        2. İstenen seçenekleri yapılandırın
        3. Analiz sonucunu alın (ekran görüntüleri, HTML, loglar)
        """,
        version="2.0.0",
        terms_of_service="https://example.com/terms/",
        contact=contact_info,
        license_info=license_info,
        openapi_tags=tags_metadata,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    app = FastAPI(
        title="SB-Scraper API",
        description="""
        SB-Scraper, SeleniumBase tabanlı gelişmiş web scraping API'sidir.
        
        ## Özellikler:
        
        * **Çoklu Tarama Modu:** Ham URL ve ana domain taraması
        * **Mobil Görünüm:** Mobil cihaz ekran görüntüleri
        * **Arama Motoru Entegrasyonu:** Google ve DuckDuckGo sonuçları
        * **HTML Kaynak Kodu:** Sayfa kaynak kodlarını alma
        * **Black-list Koruması:** İstenmeyen domain'leri filtreleme
        * **Anti-Detection:** WebDriver tespitini önleme
        
        ## Kullanım:
        
        1. Taranacak URL'i belirtin
        2. İstenen seçenekleri yapılandırın
        3. Analiz sonucunu alın (ekran görüntüleri, HTML, loglar)
        """,
        version="2.0.0",
        terms_of_service="https://example.com/terms/",
        contact=contact_info,
        license_info=license_info,
        openapi_tags=tags_metadata,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

# Custom OpenAPI entegrasyonu
app.openapi = lambda: custom_openapi(app)

# Static dosyaları ekle
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS Middleware (Opsiyonel)
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

# Middleware ekle
app.middleware("http")(request_tracker_middleware)

# ==================== POSTGRESQL HEALTH CHECK MIDDLEWARE ====================
@app.middleware("http")
async def postgres_health_check_middleware(request: Request, call_next: Any) -> Response:
    """
    PostgreSQL bağlantısını kontrol et.
    PostgreSQL çökerse write işlemlerini durdur.
    
    Args:
        request: FastAPI Request nesnesi
        call_next: Sonraki middleware/endpoint fonksiyonu
    
    Returns:
        Response: HTTP yanıtı
    
    Raises:
        HTTPException: PostgreSQL bağlantısı yoksa 503 Service Unavailable
    """
    # Tüm write endpoint'lerinde kontrol et (POST, PUT, PATCH, DELETE)
    write_methods = ["POST", "PUT", "PATCH", "DELETE"]
    if request.method in write_methods:
        if not await postgres_logger.health_check():
            logger.error(f"❌ PostgreSQL bağlantısı yok! {request.method} {request.url.path} durduruluyor.")
            raise HTTPException(
                status_code=503,
                detail="PostgreSQL bağlantısı yok. Lütfen sistem yöneticisine başvurun."
            )
    
    response = await call_next(request)
    return response

# ==================== RESPONSE CACHING (Opsiyonel) ====================
class SimpleCache:
    """
    Basit in-memory cache (LRU benzeri) - Thread-safe
    
    Cache, TTL (Time To Live) süresi boyunca verileri tutar.
    TTL süresi dolan kayıtlar otomatik olarak silinir.
    Thread-safe: Tüm işlemler lock ile korunur.
    """
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Cache başlat
        
        Args:
            max_size: Maksimum cache boyutu
            ttl: Cache TTL süresi (saniye)
        """
        self._cache: Dict[str, tuple] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()  # Thread-safety için lock

    def get(self, key: str) -> Optional[Any]:
        """
        Cache'ten veri oku
        
        Args:
            key: Cache anahtarı
        
        Returns:
            Cache'teki veri veya None
        """
        with self._lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return data
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Cache'e veri yaz
        
        Args:
            key: Cache anahtarı
            value: Cache'e yazılacak veri
        """
        with self._lock:
            if len(self._cache) >= self._max_size:
                # En eski kaydı sil
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Cache'i temizle"""
        with self._lock:
            self._cache.clear()


# Global cache instance
response_cache = SimpleCache(
    max_size=settings.response_cache_max_size,
    ttl=settings.response_cache_ttl
)


def cache_response(ttl: int = 300):
    """
    Response caching decorator
    
    Args:
        ttl: Cache TTL süresi (saniye)
    
    Returns:
        Decorator fonksiyonu
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.response_caching_enabled:
                return await func(*args, **kwargs)
            
            # Cache key oluştur
            cache_key = hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()
            
            # Cache'ten oku
            cached = response_cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Fonksiyonu çalıştır
            result = await func(*args, **kwargs)
            
            # Cache'e yaz
            response_cache.set(cache_key, result)
            return result
        return wrapper
    return decorator


# ==================== HEALTH CHECK ENDPOINT ====================
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Kapsamlı health check endpoint
    
    Tüm servislerin durumunu kontrol eder:
    - PostgreSQL bağlantısı
    - Browser Manager (Chrome driver)
    - Task Queue
    - Memory Monitor
    - System Monitor
    - Cache
    
    Returns:
        Dict[str, Any]: Sağlık durumu bilgileri
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # PostgreSQL bağlantısı kontrolü
    try:
        from app.db.connection import connection_pool
        pg_healthy = await postgres_logger.health_check()
        health_status["services"]["postgresql"] = {
            "status": "healthy" if pg_healthy else "unhealthy",
            "pool_initialized": connection_pool._initialized if hasattr(connection_pool, '_initialized') else False
        }
    except Exception as e:
        health_status["services"]["postgresql"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Browser Manager kontrolü
    try:
        browser_healthy = mgr.driver is not None
        health_status["services"]["browser"] = {
            "status": "healthy" if browser_healthy else "unhealthy",
            "driver_available": browser_healthy
        }
    except Exception as e:
        health_status["services"]["browser"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Task Queue kontrolü
    try:
        queue_stats = task_queue.get_stats()
        health_status["services"]["task_queue"] = {
            "status": "healthy",
            "running": queue_stats["running"],
            "queue_size": queue_stats["queue_size"],
            "worker_count": queue_stats["worker_count"]
        }
    except Exception as e:
        health_status["services"]["task_queue"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Memory Monitor kontrolü
    try:
        memory_monitor = get_memory_monitor()
        health_status["services"]["memory_monitor"] = {
            "status": "healthy",
            "running": memory_monitor._running if hasattr(memory_monitor, '_running') else False
        }
    except Exception as e:
        health_status["services"]["memory_monitor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # System Monitor kontrolü
    try:
        system_monitor = get_system_monitor()
        health_status["services"]["system_monitor"] = {
            "status": "healthy",
            "running": system_monitor._running if hasattr(system_monitor, '_running') else False
        }
    except Exception as e:
        health_status["services"]["system_monitor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Cache kontrolü
    try:
        health_status["services"]["cache"] = {
            "status": "healthy",
            "enabled": settings.response_caching_enabled
        }
    except Exception as e:
        health_status["services"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


# Browser Manager (Singleton)
mgr = BrowserManager()

# ==================== STARTUP EVENT ====================
@app.on_event("startup")
async def startup_event() -> None:
    """
    Uygulama başladığında PostgreSQL bağlantısını başlat ve task queue'yi başlat
    
    Raises:
        Exception: PostgreSQL bağlantı hatası
    """
    from app.db.connection import connection_pool
    
    try:
        await connection_pool.initialize()
        logger.info("✅ PostgreSQL bağlantısı başlatıldı.")
    except Exception as e:
        logger.error(f"❌ PostgreSQL bağlantı hatası: {e}")
        raise
    
    # Task Queue'yi başlat
    try:
        task_queue.start(worker_count=2)
        logger.info("✅ Task Queue başlatıldı.")
    except Exception as e:
        logger.error(f"❌ Task Queue başlatma hatası: {e}")
        # Task queue hatası kritik değil, uygulamayı durdurma
    
    # Memory Monitor'ü başlat
    try:
        memory_monitor = get_memory_monitor()
        
        # Cleanup callback'leri ekle
        memory_monitor.add_cleanup_callback(task_queue.clear_completed_tasks)
        
        # Memory monitor'ü başlat
        memory_monitor.start()
        logger.info("✅ Memory Monitor başlatıldı.")
    except Exception as e:
        logger.error(f"❌ Memory Monitor başlatma hatası: {e}")
        # Memory monitor hatası kritik değil, uygulamayı durdurma
    
    # System Monitor'ü başlat
    try:
        system_monitor = get_system_monitor()
        
        # BrowserManager cleanup callback'ini ekle
        system_monitor.add_cleanup_callback(mgr.cleanup_temp_files)
        
        # System monitor'ü başlat
        system_monitor.start()
        logger.info("✅ System Monitor başlatıldı.")
    except Exception as e:
        logger.error(f"❌ System Monitor başlatma hatası: {e}")
        # System monitor hatası kritik değil, uygulamayı durdurma

# ==================== SHUTDOWN EVENT ====================
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Uygulama kapanırken tüm kaynakları güvenli şekilde serbest bırak
    Graceful shutdown - tüm servisler düzgün şekilde durdurulur
    
    Raises:
        Exception: Kaynak kapatma hatası
    """
    logger.info("🔄 Graceful shutdown başlatılıyor...")
    
    # 1. Memory Monitor'ü durdur
    try:
        memory_monitor = get_memory_monitor()
        memory_monitor.stop()
        logger.info("🔌 Memory Monitor durduruldu.")
    except Exception as e:
        logger.error(f"❌ Memory Monitor durdurma hatası: {e}")
    
    # 2. System Monitor'ü durdur
    try:
        system_monitor = get_system_monitor()
        system_monitor.stop()
        logger.info("🔌 System Monitor durduruldu.")
    except Exception as e:
        logger.error(f"❌ System Monitor durdurma hatası: {e}")
    
    # 3. Task Queue'yi durdur (önce kuyruğu boşalt)
    try:
        # Kuyrukta bekleyen task'ların bitmesini bekle
        import asyncio
        max_wait_seconds = 30
        waited = 0
        while task_queue.get_queue_size() > 0 and waited < max_wait_seconds:
            await asyncio.sleep(1)
            waited += 1
        
        if waited >= max_wait_seconds:
            logger.warning(f"⚠️ Task queue timeout: {task_queue.get_queue_size()} task bekliyor")
        
        task_queue.stop()
        logger.info("🔌 Task Queue durduruldu.")
    except Exception as e:
        logger.error(f"❌ Task Queue durdurma hatası: {e}")
    
    # 4. Browser Manager'ı temizle
    try:
        mgr.cleanup_temp_files()
        logger.info("🔌 Browser Manager temizlendi.")
    except Exception as e:
        logger.error(f"❌ Browser Manager temizleme hatası: {e}")
    
    # 5. PostgreSQL bağlantısını kapat
    from app.db.connection import connection_pool
    from app.core.postgres_logger import postgres_handler
    
    try:
        # Önce postgres handler'ı durdur
        postgres_handler.stop_consumer()
        logger.info("🔌 PostgreSQL Handler durduruldu.")
        
        # Sonra connection pool'ı kapat
        await connection_pool.close()
        logger.info("🔌 PostgreSQL bağlantısı kapatıldı.")
    except Exception as e:
        logger.error(f"❌ PostgreSQL bağlantı kapatma hatası: {e}")
    
    # 6. Cache'i temizle
    try:
        response_cache.clear()
        logger.info("🔌 Response cache temizlendi.")
    except Exception as e:
        logger.error(f"❌ Cache temizleme hatası: {e}")
    
    logger.info("✅ Graceful shutdown tamamlandı.")

# ==================== LOG ROUTER ====================
log_router = APIRouter(prefix="/api", tags=["Loglar"])


@app.get("/logs")
@cache_response(ttl=settings.response_cache_ttl)
async def get_logs(count: int = 100, level: str = None) -> Dict[str, Any]:
    """
    PostgreSQL'den logları oku

    Query Parameters:
    - count: Kaç log okunacak (default: 100)
    - level: Log seviyesi (INFO, ERROR, DEBUG)
    
    Returns:
        Logları içeren dict
    """
    logs = await postgres_logger.get_logs(count=count, level=level)
    return {
        "logs": logs
    }


@app.get("/stats/requests")
@cache_response(ttl=settings.response_cache_ttl)
async def get_request_stats(count: int = 100) -> Dict[str, Any]:
    """
    Request loglarını al
    
    Query Parameters:
    - count: Kaç request logu okunacak (default: 100)
    
    Returns:
        Request logları listesi (ip, method, path, headers, body, etc.)
    """
    requests = await postgres_logger.get_requests(count=count)
    return {
        "requests": requests
    }


@app.get("/stats/requests/filter")
@cache_response(ttl=settings.response_cache_ttl)
async def filter_requests(
    ip: str = None,
    method: str = None,
    path: str = None,
    count: int = 100
) -> Dict[str, Any]:
    """
    Request loglarını filtrele
    
    Query Parameters:
    - ip: IP adresi ile filtrele (opsiyonel)
    - method: HTTP method ile filtrele (opsiyonel)
    - path: Path ile filtrele (opsiyonel)
    - count: Kaç sonuç döndürülecek (default: 100)
    
    Returns:
        Filtrelenmiş request logları
    """
    requests = await postgres_logger.get_requests(count=count, ip=ip, path=path)
    
    # Method filtresi
    if method:
        requests = [req for req in requests if req.get("method") == method]
    
    return {
        "requests": requests,
        "total": len(requests)
    }


@app.get("/health/postgres")
@cache_response(ttl=settings.response_cache_ttl)
async def postgres_health() -> Dict[str, str]:
    """
    PostgreSQL bağlantı durumunu kontrol et
    
    Returns:
        PostgreSQL sağlık durumu
    """
    is_healthy = await postgres_logger.health_check()
    return {
        "status": "healthy" if is_healthy else "unhealthy"
    }


# Log router'ı uygulamaya ekle
app.include_router(log_router)


# ==================== ROOT ENDPOINT ====================
@app.get(
    "/", 
    tags=["Genel"],
    summary="API Durum Kontrolü",
    description="""
    API'nin çalışıp çalışmadığını kontrol eder.
    
    Bu endpoint, API'nin aktif olduğunu doğrulamak için kullanılır.
    Herhangi bir parametre gerektirmez.
    """,
    responses={
        200: {
            "description": "API çalışıyor",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "message": "SB-Scraper API is running"
                    }
                }
            }
        }
    }
)
def root() -> Dict[str, str]:
    """
    API durumunu kontrol et
    
    Returns:
        JSON yanıt: API durumu bilgisi
    """
    return {"status": "ok", "message": "SB-Scraper API is running"}


# ==================== HEALTH ENDPOINT ====================
@app.get(
    "/health",
    tags=["Genel"],
    summary="Sağlık Kontrolü",
    description="""
    API'nin ve tarayıcının sağlık durumunu kontrol eder.
    
    Bu endpoint, API'nin yanı sıra tarayıcı bağlantısının da sağlıklı olup olmadığını doğrular.
    """,
    responses={
        200: {
            "description": "Sistem sağlıklı",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy"
                    }
                }
            }
        }
    }
)
async def health() -> Dict[str, Any]:
    """
    Sağlık kontrolü (Detaylı versiyon)
    
    Returns:
        JSON yanıt: Sistem durumu
    """
    # PostgreSQL sağlık kontrolü
    postgres_status = "healthy" if await postgres_logger.health_check() else "unhealthy"
    
    # Task queue durumu
    task_queue_stats = task_queue.get_stats()
    task_queue_status = "running" if task_queue_stats.get("running", False) else "stopped"
    
    # Memory durumu
    memory_monitor = get_memory_monitor()
    memory_info = memory_monitor.get_memory_info()
    
    # Genel sistem durumu
    overall_status = "healthy"
    if postgres_status != "healthy":
        overall_status = "degraded"
    elif task_queue_status != "running":
        overall_status = "degraded"
    elif memory_info.get("rss_mb", 0) > memory_info.get("critical_threshold_mb", 2048):
        overall_status = "critical"
    elif memory_info.get("rss_mb", 0) > memory_info.get("threshold_mb", 1024):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "postgres": postgres_status,
        "browser": "ready" if mgr.driver else "not_ready",
        "task_queue": task_queue_status,
        "task_queue_stats": task_queue_stats,
        "memory": memory_info
    }


# ==================== ANALYZE ENDPOINT ====================
@app.post(
    "/analyze",
    tags=["Scraping"],
    summary="URL Analizi Yap",
    description="""
    Belirtilen URL'i tarar ve çeşitli çıktılar üretir.
    
    Bu endpoint, verilen URL için web scraping işlemi gerçekleştirir.
    Ekran görüntüleri, HTML kaynak kodları ve loglar döndürür.
    
    ## Seçenekler:
    
    - **wait_time:** Sayfa yükleme bekleme süresi (saniye)
    - **process_raw_url:** Ham URL'i işle
    - **process_main_domain:** Ana domain'i işle
    - **get_html:** HTML kaynak kodunu al
    - **get_mobile_ss:** Mobil ekran görüntüsü al
    - **get_google_search:** Google arama sonuçlarını al
    - **get_ddg_search:** DuckDuckGo arama sonuçlarını al
    - **capture_network_logs:** Ağ loglarını yakala
    - **force_refresh:** Tarayıcıyı zorla yenile
    
    ## Hata Kodları:
    
    - **BROWSER_BUSY:** Tarayıcı şu an başka bir işlemde
    - **BROWSER_INIT_FAILED:** Tarayıcı başlatılamadı
    - **BLACKLISTED_DOMAIN:** Domain kara listede
    - **INVALID_URL:** Geçersiz URL formatı
    """,
    responses={
        200: {
            "description": "Analiz başarılı",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "raw_desktop_ss": "base64_encoded_image",
                        "raw_html": "<html>...</html>",
                        "logs": ["Log 1", "Log 2"],
                        "duration": 5.23
                    }
                }
            }
        },
        400: {
            "description": "Geçersiz istek",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "INVALID_URL",
                        "message": "Geçersiz URL formatı",
                        "details": "https://example.com"
                    }
                }
            }
        },
        403: {
            "description": "Kara listede",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "BLACKLISTED_DOMAIN",
                        "message": "Bu domain kara listede",
                        "details": "example.com"
                    }
                }
            }
        },
        503: {
            "description": "Tarayıcı hatası",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "BROWSER_BUSY",
                        "message": "Tarayıcı şu an meşgul",
                        "details": None
                    }
                }
            }
        }
    }
)
async def analyze(
    request: ScrapeRequest,
    _: None = Depends(verify_api_key),
    http_request: Request = None
) -> Dict[str, Any]:
    """
    URL analizi yap ve sonuçları döndür
    
    Args:
        request: ScrapeRequest nesnesi
        _: Authentication dependency (opsiyonel)
        http_request: FastAPI Request nesnesi (rate limiting için)
    
    Returns:
        Dict[str, Any]: Analiz sonuçları
    
    Raises:
        HTTPException: Hata durumunda
    """
    # Rate limiting kontrolü (opsiyonel)
    if settings.rate_limiting_enabled and RATE_LIMITING_AVAILABLE and http_request:
        limiter = app.state.limiter
        try:
            limiter.check_request_limit(http_request)
        except RateLimitExceeded as e:
            raise SBScraperError(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="İstek limiti aşıldı",
                details=str(e)
            )
    
    try:
        # Blacklist kontrolü
        from app.core.blacklist import blacklist_manager
        
        if blacklist_manager.is_blacklisted(request.url):
            raise SBScraperError(
                error_code=ErrorCode.BLACKLISTED_DOMAIN,
                message="Bu domain kara listede",
                details=blacklist_manager._extract_domain(request.url)
            )
        
        # Tarayıcı durumunu kontrol et
        if not mgr.driver:
            try:
                mgr.start_driver()
            except Exception as e:
                logger.error(f"❌ Tarayıcı başlatılamadı: {e}", exc_info=True)
                raise SBScraperError(
                    error_code=ErrorCode.BROWSER_INIT_FAILED,
                    message="Tarayıcı başlatılamadı",
                    details=str(e)
                )
        
        # Scraping işlemini gerçekleştir
        response = mgr.process(request)
        
        # Pydantic v2 için model_dump() kullanılır
        return response.model_dump()
    
    except SBScraperError as e:
        # SBScraperError için özel yanıt
        logger.warning(f"⚠️ SBScraperError: {e.error_code} - {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    
    except Exception as e:
        # Beklenmeyen hatalar için genel yanıt
        logger.error(f"❌ Analyze endpoint hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "İç sunucu hatası oluştu",
                "details": str(e) if settings.log_level == "DEBUG" else None
            }
        )


# ==================== TASK QUEUE ENDPOINTS ====================
@app.get(
    "/tasks/stats",
    tags=["Görevler"],
    summary="Task Queue İstatistikleri",
    description="""
    Task queue'nin istatistiklerini döndürür.
    
    Bu endpoint, kuyruk boyutu, toplam görev sayısı, worker sayısı
    ve görev durumları hakkında bilgi sağlar.
    """,
    responses={
        200: {
            "description": "İstatistikler",
            "content": {
                "application/json": {
                    "example": {
                        "queue_size": 5,
                        "total_tasks": 10,
                        "worker_count": 2,
                        "running": True,
                        "task_counts": {
                            "pending": 5,
                            "running": 2,
                            "completed": 2,
                            "failed": 1
                        }
                    }
                }
            }
        }
    }
)
async def get_task_queue_stats() -> Dict[str, Any]:
    """
    Task queue istatistiklerini al
    
    Returns:
        Dict[str, Any]: İstatistikler
    """
    return task_queue.get_stats()


@app.get(
    "/tasks/{task_id}",
    tags=["Görevler"],
    summary="Görev Detayları",
    description="""
    Belirtilen görevin detaylarını döndürür.
    
    Args:
        task_id: Görev ID'si
    
    Returns:
        Dict[str, Any]: Görev detayları
    """,
    responses={
        200: {
            "description": "Görev detayları",
            "content": {
                "application/json": {
                    "example": {
                        "id": "task_1",
                        "name": "example_task",
                        "status": "completed",
                        "result": "success",
                        "error": None,
                        "created_at": 1234567890.0,
                        "started_at": 1234567891.0,
                        "completed_at": 1234567895.0,
                        "retry_count": 0,
                        "max_retries": 3
                    }
                }
            }
        },
        404: {
            "description": "Görev bulunamadı",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Görev bulunamadı"
                    }
                }
            }
        }
    }
)
async def get_task_details(task_id: str) -> Dict[str, Any]:
    """
    Görev detaylarını al
    
    Args:
        task_id: Görev ID'si
    
    Returns:
        Dict[str, Any]: Görev detayları
    
    Raises:
        HTTPException: Görev bulunamazsa
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Görev bulunamadı"
        )
    return task


@app.get(
    "/tasks",
    tags=["Görevler"],
    summary="Tüm Görevler",
    description="""
    Tüm görevleri döndürür.
    
    Bu endpoint, kuyruktaki tüm görevlerin listesini sağlar.
    """,
    responses={
        200: {
            "description": "Tüm görevler",
            "content": {
                "application/json": {
                    "example": {
                        "task_1": {
                            "id": "task_1",
                            "name": "example_task",
                            "status": "completed"
                        },
                        "task_2": {
                            "id": "task_2",
                            "name": "another_task",
                            "status": "pending"
                        }
                    }
                }
            }
        }
    }
)
async def get_all_tasks() -> Dict[str, Dict[str, Any]]:
    """
    Tüm görevleri al
    
    Returns:
        Dict[str, Dict[str, Any]]: Tüm görevler
    """
    return task_queue.get_all_tasks()


@app.delete(
    "/tasks/completed",
    tags=["Görevler"],
    summary="Tamamlanan Görevleri Temizle",
    description="""
    Tamamlanan veya başarısız görevleri temizler.
    
    Bu endpoint, tamamlanan veya başarısız görevleri
    bellekten kaldırır.
    """,
    responses={
        200: {
            "description": "Temizlenen görev sayısı",
            "content": {
                "application/json": {
                    "example": {
                        "cleared_count": 5
                    }
                }
            }
        }
    }
)
async def clear_completed_tasks() -> Dict[str, int]:
    """
    Tamamlanan görevleri temizle
    
    Returns:
        Dict[str, int]: Temizlenen görev sayısı
    """
    cleared_count = task_queue.clear_completed_tasks()
    return {"cleared_count": cleared_count}


@app.get(
    "/stats/memory",
    tags=["Genel"],
    summary="Memory İstatistikleri",
    description="""
    Uygulamanın memory kullanımını gösterir.
    
    Bu endpoint, RAM kullanımı, memory yüzdesi ve
    threshold değerleri hakkında bilgi sağlar.
    """,
    responses={
        200: {
            "description": "Memory istatistikleri",
            "content": {
                "application/json": {
                    "example": {
                        "rss_mb": 512.5,
                        "vms_mb": 1024.0,
                        "percent": 2.5,
                        "threshold_mb": 1024,
                        "critical_threshold_mb": 2048,
                        "running": True
                    }
                }
            }
        }
    }
)
async def get_memory_stats() -> Dict[str, Any]:
    """
    Memory istatistiklerini al
    
    Returns:
        Dict[str, Any]: Memory bilgileri
    """
    memory_monitor = get_memory_monitor()
    return memory_monitor.get_memory_info()


@app.get(
    "/stats/system",
    tags=["Genel"],
    summary="Sistem İstatistikleri",
    description="""
    Uygulamanın sistem kaynaklarını gösterir.
    
    Bu endpoint, ana process ve Chrome süreçlerinin RAM/CPU kullanımı
    ile /tmp disk kullanımı hakkında bilgi sağlar.
    """,
    responses={
        200: {
            "description": "Sistem istatistikleri",
            "content": {
                "application/json": {
                    "example": {
                        "main_process": {
                            "pid": 12345,
                            "rss_mb": 512.5,
                            "vms_mb": 1024.0,
                            "percent": 2.5,
                            "cpu_percent": 1.2
                        },
                        "chrome_processes": {
                            "count": 5,
                            "total_ram_mb": 250.0,
                            "processes": [
                                {
                                    "pid": 12346,
                                    "name": "chrome",
                                    "ram_mb": 50.0,
                                    "cpu_percent": 0.5
                                }
                            ]
                        },
                        "tmp_usage": {
                            "path": "/tmp",
                            "used_mb": 512.0,
                            "total_mb": 1024.0,
                            "free_mb": 512.0,
                            "percent": 50.0,
                            "threshold_mb": 1024
                        },
                        "check_interval": 60,
                        "running": True
                    }
                }
            }
        }
    }
)
async def get_system_stats() -> Dict[str, Any]:
    """
    Sistem istatistiklerini al
    
    Returns:
        Dict[str, Any]: Sistem bilgileri
    """
    system_monitor = get_system_monitor()
    return system_monitor.get_system_info()
