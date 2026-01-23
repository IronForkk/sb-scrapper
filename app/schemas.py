"""
Pydantic Modelleri
Request ve Response şemaları
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal


class ScrapeRequest(BaseModel):
    """
    Web Scraping İstek Şeması
    
    Bu şema, bir web sitesini taramak için gerekli tüm parametreleri içerir.
    """
    
    # ==================== ZORUNLU ALANLAR ====================
    url: str = Field(
        ..., 
        title="Hedef URL",
        description="Taranacak web sitesinin adresi (http/https dahil)",
        examples=["https://www.example.com", "example.com"],
        min_length=3,
        max_length=2048
    )
    
    # ==================== ZAMAN AYARLARI ====================
    wait_time: int = Field(
        8, 
        title="Bekleme Süresi",
        description="""
        Sayfa yüklendikten sonra beklenecek saniye (Javascriptlerin oturması için).
        
        Düşük değerler sayfanın tam yüklenmemesine neden olabilir.
        Yüksek değerler işlem süresini uzatabilir.
        """,
        ge=1, 
        le=60,
        examples=[5, 8, 10, 15]
    )
    
    # ==================== İŞLEM AYARLARI ====================
    process_raw_url: bool = Field(
        True, 
        title="Ham URL Tara",
        description="Verilen URL'i doğrudan tarar. Ana URL ile aynıysa ana domain taraması atlanır.",
        examples=[True, False]
    )
    
    process_main_domain: bool = Field(
        True, 
        title="Ana Domain Tara",
        description="URL'in ana domainini (homepage) de tarar. Örn: example.com/contact için example.com",
        examples=[True, False]
    )
    
    # ==================== ÇIKTI AYARLARI ====================
    get_html: bool = Field(
        True, 
        title="HTML Kaynak Kodunu Al",
        description="Sayfanın HTML kaynak kodunu Base64 formatında döndürür",
        examples=[True, False]
    )
    
    get_mobile_ss: bool = Field(
        True, 
        title="Mobil Ekran Görüntüsü Al",
        description="Mobil görünümde (375x812) ekran görüntüsü alır",
        examples=[True, False]
    )
    
    # ==================== ARAMA MOTORLARI ====================
    get_google_search: bool = Field(
        True, 
        title="Google Arama Sonucu Al",
        description="Siteyi Google'da aratıp sonuç ekran görüntüsünü alır",
        examples=[True, False]
    )
    
    get_google_html: bool = Field(
        True, 
        title="Google HTML Al",
        description="Google arama sonucunun HTML'ini alır",
        examples=[True, False]
    )
    
    get_ddg_search: bool = Field(
        True, 
        title="DuckDuckGo Arama Sonucu Al",
        description="Siteyi DuckDuckGo'da aratıp sonuç ekran görüntüsünü alır",
        examples=[True, False]
    )
    
    get_ddg_html: bool = Field(
        True, 
        title="DuckDuckGo HTML Al",
        description="DuckDuckGo arama sonucunun HTML'ini alır",
        examples=[True, False]
    )
    
    # ==================== SİSTEM ====================
    force_refresh: bool = Field(
        False, 
        title="Tarayıcıyı Sıfırla",
        description="""
        Tarayıcıyı zorla yeniden başlatır. Yeni bir oturum başlatır.
        User Agent ve noise değerleri yenilenir.
        """,
        examples=[True, False]
    )
    
    # ==================== VALIDASYON ====================
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """URL validasyonu"""
        if not v:
            raise ValueError('URL boş olamaz')
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        return v
    
    # ==================== SWAGGER ÖRNEKLERİ ====================
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com",
                    "wait_time": 10,
                    "process_raw_url": True,
                    "process_main_domain": False,
                    "get_html": True,
                    "get_mobile_ss": True,
                    "get_google_search": True,
                    "get_google_html": True,
                    "get_ddg_search": False,
                    "get_ddg_html": False,
                    "force_refresh": False
                },
                {
                    "url": "example.com",
                    "wait_time": 5,
                    "process_raw_url": True,
                    "process_main_domain": True,
                    "get_html": False,
                    "get_mobile_ss": True,
                    "get_google_search": True,
                    "get_ddg_search": True,
                    "force_refresh": True
                }
            ]
        }
    }


class ScrapeResponse(BaseModel):
    """
    Web Scraping Yanıt Şeması
    
    Tarama işleminin sonucunu içerir.
    """
    
    # ==================== DURUM ====================
    status: Literal["success", "error", "blacklisted", "processing"] = Field(
        ...,
        title="İşlem Durumu",
        description="""
        İşlemin sonucunu belirten durum kodu:
        
        - `success`: İşlem başarıyla tamamlandı
        - `error`: İşlem sırasında hata oluştu
        - `blacklisted`: Domain black-list'te bulundu
        - `processing`: İşlem devam ediyor (geçici durum)
        """,
        examples=["success", "error", "blacklisted", "processing"]
    )
    
    # ==================== EKRAN GÖRÜNTÜLERİ (Base64) ====================
    raw_desktop_ss: Optional[str] = Field(
        None,
        title="Masaüstü Ekran Görüntüsü",
        description="Ham URL için masaüstü görünümü ekran görüntüsü (Base64 PNG)",
        examples=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."]
    )
    
    raw_mobile_ss: Optional[str] = Field(
        None,
        title="Mobil Ekran Görüntüsü",
        description="Ham URL için mobil görünüm ekran görüntüsü (Base64 PNG, 375x812)",
        examples=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."]
    )
    
    main_desktop_ss: Optional[str] = Field(
        None,
        title="Ana Domain Masaüstü Ekran Görüntüsü",
        description="Ana domain için masaüstü görünümü ekran görüntüsü (Base64 PNG)",
        examples=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."]
    )
    
    google_ss: Optional[str] = Field(
        None,
        title="Google Arama Sonucu Ekran Görüntüsü",
        description="Google arama sonucunun ekran görüntüsü (Base64 PNG)",
        examples=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."]
    )
    
    ddg_ss: Optional[str] = Field(
        None,
        title="DuckDuckGo Arama Sonucu Ekran Görüntüsü",
        description="DuckDuckGo arama sonucunun ekran görüntüsü (Base64 PNG)",
        examples=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."]
    )
    
    # ==================== HTML KAYNAK KODLARI (Base64) ====================
    raw_html: Optional[str] = Field(
        None,
        title="Ham URL HTML Kaynak Kodu",
        description="Ham URL'in HTML kaynak kodu (Base64)",
        examples=["PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4="]
    )
    
    google_html: Optional[str] = Field(
        None,
        title="Google Arama Sonucu HTML",
        description="Google arama sonucunun HTML kaynak kodu (Base64)",
        examples=["PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4="]
    )
    
    ddg_html: Optional[str] = Field(
        None,
        title="DuckDuckGo Arama Sonucu HTML",
        description="DuckDuckGo arama sonucunun HTML kaynak kodu (Base64)",
        examples=["PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4="]
    )
    
    # ==================== LOG VE SÜRE ====================
    logs: List[str] = Field(
        default_factory=list,
        title="İşlem Logları",
        description="İşlem sırasında oluşan adım adım loglar",
        examples=[["Adım 1: Ham URL -> https://example.com", "✅ Google Çerezi Tıklandı"]]
    )
    
    duration: float = Field(
        ...,
        title="İşlem Süresi",
        description="İşlemin toplam süresi (saniye cinsinden)",
        ge=0,
        examples=[5.23, 12.45, 30.1]
    )
    
    # ==================== BLACK-LIST ====================
    blacklisted_domain: Optional[str] = Field(
        None,
        title="Black-list'e Takılan Domain",
        description="Eğer status='blacklisted' ise, bu alan hangi domain'in black-list'te olduğunu gösterir",
        examples=["malicious-site.com"]
    )
    
    # ==================== SWAGGER ÖRNEKLERİ ====================
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "raw_desktop_ss": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "raw_mobile_ss": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "raw_html": "PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4=",
                    "main_desktop_ss": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "google_ss": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "google_html": "PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4=",
                    "ddg_ss": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "ddg_html": "PGh0bWw+PGhlYWQ+Li4uPC9oZWFkPjwvaHRtbD4=",
                    "logs": ["Adım 1: Ham URL -> https://example.com", "✅ Bitti"],
                    "duration": 12.45,
                    "blacklisted_domain": None
                },
                {
                    "status": "blacklisted",
                    "logs": ["🚫 Domain black-list'te: malicious-site.com"],
                    "duration": 0.05,
                    "blacklisted_domain": "malicious-site.com"
                },
                {
                    "status": "error",
                    "logs": ["❌ HATA: Sayfa yüklenemedi"],
                    "duration": 5.23,
                    "blacklisted_domain": None
                }
            ]
        }
    }
