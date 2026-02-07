"""
FastAPI Ana Uygulaması
SB-Scraper API endpoint'i - Tek endpoint (/scrape)
"""
from typing import Dict, Any
import time
from fastapi import FastAPI, HTTPException, Request

from app.config import settings
from app.schemas import ScrapeRequest, ScrapeResponse
from app.core.browser import BrowserManager
from app.core.logger import logger
from app.core.logger import PostgresLogger
from app.errors import SBScraperError, ErrorCode


# ==================== FASTAPI UYGULAMASI ====================
app = FastAPI(
    title="SB-Scraper API",
    description="""
    SB-Scraper, SeleniumBase tabanlı web scraping API'sidir.
    
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
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Browser Manager (Singleton)
mgr = BrowserManager()
postgres_logger = PostgresLogger()


# ==================== STARTUP EVENT ====================
@app.on_event("startup")
def startup_event() -> None:
    """
    Uygulama başladığında PostgreSQL bağlantısını başlat
    
    Raises:
        Exception: PostgreSQL bağlantı hatası
    """
    postgres_logger.initialize()


# ==================== SHUTDOWN EVENT ====================
@app.on_event("shutdown")
def shutdown_event() -> None:
    """
    Uygulama kapanırken tüm kaynakları güvenli şekilde serbest bırak
    
    Raises:
        Exception: Kaynak kapatma hatası
    """
    logger.info("Graceful shutdown başlatılıyor...")
    
    # Browser Manager'ı temizle
    try:
        mgr.cleanup_temp_files()
        logger.info("Browser Manager temizlendi.")
    except Exception as e:
        logger.error(f"Browser Manager temizleme hatası: {e}")
    
    # PostgreSQL bağlantısını kapat
    try:
        postgres_logger.close()
        logger.info("PostgreSQL bağlantısı kapatıldı.")
    except Exception as e:
        logger.error(f"PostgreSQL bağlantı kapatma hatası: {e}")
    
    logger.info("Graceful shutdown tamamlandı.")


# ==================== SCRAPE ENDPOINT ====================
@app.post(
    "/scrape",
    tags=["Scraping"],
    summary="URL Scraping İşlemi Yap",
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
    
    ## Hata Kodları:
    
    - **BROWSER_BUSY:** Tarayıcı şu an başka bir işlemde
    - **BROWSER_INIT_FAILED:** Tarayıcı başlatılamadı
    - **BLACKLISTED_DOMAIN:** Domain kara listede
    - **INVALID_URL:** Geçersiz URL formatı
    """,
    responses={
        200: {
            "description": "Scraping başarılı",
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
def scrape(
    request: ScrapeRequest,
    http_request: Request = None
) -> Dict[str, Any]:
    """
    URL scraping işlemi yap ve sonuçları döndür
    
    Args:
        request: ScrapeRequest nesnesi
        http_request: FastAPI Request nesnesi
    
    Returns:
        Dict[str, Any]: Scraping sonuçları
    
    Raises:
        HTTPException: Hata durumunda
    """
    start_time = time.time()
    
    # Domain'i çıkar (en başta yap)
    from urllib.parse import urlparse
    parsed = urlparse(request.url)
    domain = parsed.netloc
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # ==================== REQUEST LOGGING ====================
    # Request bilgilerini hazırla
    request_data = {
        'ip': http_request.client.host if http_request else None,
        'port': http_request.client.port if http_request else None,
        'method': http_request.method if http_request else 'POST',
        'path': str(http_request.url.path) if http_request else '/scrape',
        'full_url': str(http_request.url) if http_request else None,
        'headers': dict(http_request.headers) if http_request else {},
        'query_params': dict(http_request.query_params) if http_request else {},
        'user_agent': http_request.headers.get('user-agent') if http_request else None,
        # .clinerules: Request body loglama izinli, sadece Response body loglanmamalı
        'body': request.model_dump() if settings.log_request_body else None,
        'body_error': None,
        'response_status_code': None,  # Yanıt sonunda güncellenecek
        'response_time_ms': None  # Yanıt sonunda güncellenecek
    }
    
    # Sensitive header'ları filtrele
    if settings.log_request_headers:
        filtered_headers = {}
        for key, value in request_data['headers'].items():
            if key.lower() not in [h.lower() for h in settings.sensitive_headers]:
                filtered_headers[key] = value
        request_data['headers'] = filtered_headers
    else:
        request_data['headers'] = {}
    
    # Body boyutunu kontrol et
    if settings.log_request_body and request_data['body']:
        body_str = str(request_data['body'])
        if len(body_str) > settings.max_request_body_size:
            request_data['body'] = None
            request_data['body_error'] = f"Body çok büyük ({len(body_str)} > {settings.max_request_body_size})"
    
    try:
        # Blacklist kontrolü
        from app.core.blacklist import blacklist_manager
        
        if blacklist_manager.is_blacklisted(request.url):
            # Request logging - blacklisted
            request_data['response_status_code'] = 403
            request_data['response_time_ms'] = int((time.time() - start_time) * 1000)
            postgres_logger.log_request(request_data)
            
            # Domain stats logging - blacklisted
            postgres_logger.log_domain_stats(
                domain=domain,
                success_count=0,
                error_count=1,
                duration=time.time() - start_time
            )
            
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
                logger.error(f"Tarayıcı başlatılamadı: {e}", exc_info=True)
                
                # Request logging - hata
                request_data['response_status_code'] = 503
                request_data['response_time_ms'] = int((time.time() - start_time) * 1000)
                postgres_logger.log_request(request_data)
                
                # Domain stats logging - tarayıcı hatası
                postgres_logger.log_domain_stats(
                    domain=domain,
                    success_count=0,
                    error_count=1,
                    duration=time.time() - start_time
                )
                
                raise SBScraperError(
                    error_code=ErrorCode.BROWSER_INIT_FAILED,
                    message="Tarayıcı başlatılamadı",
                    details=str(e)
                )
        
        # Scraping işlemini gerçekleştir
        response = mgr.process(request)
        
        # Response status code (başarılı işlem için 200)
        status_code = 200
        
        # Domain stats logging - işlem sonucuna göre
        if response.status == "success":
            postgres_logger.log_domain_stats(
                domain=domain,
                success_count=1,
                error_count=0,
                duration=response.duration,
                raw_desktop_ss=bool(response.raw_desktop_ss),
                raw_mobile_ss=bool(response.raw_mobile_ss),
                main_desktop_ss=bool(response.main_desktop_ss),
                google_ss=bool(response.google_ss),
                ddg_ss=bool(response.ddg_ss),
                raw_html=bool(response.raw_html),
                google_html=bool(response.google_html),
                ddg_html=bool(response.ddg_html),
                network_logs=bool(response.network_logs)
            )
        else:
            postgres_logger.log_domain_stats(
                domain=domain,
                success_count=0,
                error_count=1,
                duration=response.duration
            )
        
        # Request logging - başarılı
        request_data['response_status_code'] = status_code
        request_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        postgres_logger.log_request(request_data)
        
        # Pydantic v2 için model_dump() kullanılır
        return response.model_dump()
    
    except SBScraperError as e:
        # SBScraperError için özel yanıt
        logger.warning(f"SBScraperError: {e.error_code} - {e.message}")
        
        # Request logging - SBScraperError
        request_data['response_status_code'] = 400
        request_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        postgres_logger.log_request(request_data)
        
        # Domain stats logging - SBScraperError
        postgres_logger.log_domain_stats(
            domain=domain,
            success_count=0,
            error_count=1,
            duration=time.time() - start_time
        )
        
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    
    except Exception as e:
        # Beklenmeyen hatalar için genel yanıt
        logger.error(f"Scrape endpoint hatası: {e}", exc_info=True)
        
        # Request logging - genel hata
        request_data['response_status_code'] = 500
        request_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        postgres_logger.log_request(request_data)
        
        # Domain stats logging - genel hata
        postgres_logger.log_domain_stats(
            domain=domain,
            success_count=0,
            error_count=1,
            duration=time.time() - start_time
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "İç sunucu hatası oluştu",
                "details": str(e) if settings.log_level == "DEBUG" else None
            }
        )


# ==================== HEALTH CHECK ENDPOINT ====================
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="""Uygulamanın çalışır durumda olup olmadığını kontrol eder.
    
    Bu endpoint Docker healthcheck için kullanılır ve PostgreSQL bağlantısını test eder.
    """
)
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    
    PostgreSQL bağlantısını kontrol eder ve uygulama durumunu döner.
    Docker healthcheck için kullanılır.
    
    Returns:
        Dict[str, Any]: Health check sonucu
    """
    # PostgreSQL bağlantısını test et
    db_healthy = postgres_logger.health_check()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": time.time()
    }
