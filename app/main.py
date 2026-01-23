"""
FastAPI Ana Uygulaması
SB-Scraper API endpoint'leri
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.schemas import ScrapeRequest, ScrapeResponse
from app.core.browser import BrowserManager
from app.core.logger import logger
from app.swagger_config import custom_openapi

# ==================== TAGS METADATA ====================
tags_metadata = [
    {
        "name": "Genel",
        "description": "API durum ve sağlık kontrolü endpoint'leri"
    },
    {
        "name": "Scraping",
        "description": "Web scraping ve analiz işlemleri"
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

# ==================== FASTAPI UYGULAMASI ====================
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

# Browser Manager (Singleton)
mgr = BrowserManager()


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
def root():
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
def health():
    """
    Sağlık kontrolü
    
    Returns:
        JSON yanıt: Sistem durumu
    """
    return {"status": "healthy"}


# ==================== ANALYZE ENDPOINT ====================
@app.post(
    "/analyze",
    tags=["Scraping"],
    summary="URL Analizi Yap",
    description="""
    Belirtilen URL'i tarar ve çeşitli çıktılar üretir.
    
    ## İşlem Akışı:
    
    1. **Black-list Kontrolü:** Domain black-list'te kontrol edilir
    2. **Ham URL Taraması:** İstenirse ham URL taranır
    3. **Ana Domain Taraması:** İstenirse ana domain taranır
    4. **Mobil Görünüm:** İstenirse mobil ekran görüntüsü alınır
    5. **Google Arama:** İstenirse Google'da arama yapılır
    6. **DuckDuckGo Arama:** İstenirse DuckDuckGo'da arama yapılır
    
    ## Özellikler:
    
    - Anti-detection: WebDriver tespitini önler
    - Captcha çözme: Google consent, Cloudflare, ReCaptcha vb.
    - Popup temizleme: Akıllı popup temizleme mekanizması
    - Thread-safe: Aynı anda tek işlem
    
    ## Hata Durumları:
    
    - **429 BUSY:** Tarayıcı şu anda başka bir işlemde
    - **500 Internal Error:** Beklenmeyen bir hata oluştu
    """,
    response_model=ScrapeResponse,
    responses={
        200: {
            "description": "İşlem başarıyla tamamlandı",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "raw_desktop_ss": "data:image/png;base64,iVBORw0KGgo...",
                        "raw_mobile_ss": "data:image/png;base64,iVBORw0KGgo...",
                        "logs": ["Adım 1: Ham URL -> https://example.com", "✅ Bitti"],
                        "duration": 12.45
                    }
                }
            }
        },
        429: {
            "description": "Tarayıcı meşgul (BUSY)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "BUSY"
                    }
                }
            }
        },
        500: {
            "description": "İç sunucu hatası",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Internal server error"
                    }
                }
            }
        }
    }
)
def analyze(req: ScrapeRequest):
    """
    URL analizi yap
    
    Args:
        req: ScrapeRequest nesnesi (tarama parametreleri)
    
    Returns:
        ScrapeResponse nesnesi (tarama sonuçları)
    
    Raises:
        HTTPException: 429 BUSY - Tarayıcı meşgul
    """
    return mgr.process(req)


# ==================== MAIN ENTRY POINT ====================
if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 API başlatılıyor: {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)
