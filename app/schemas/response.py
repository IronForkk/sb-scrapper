"""
Pydantic Response Şeması
Web Scraping Yanıt Şeması
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


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
    
    # ==================== NETWORK TRAFİĞİ ====================
    network_logs: List[dict] = Field(
        default_factory=list,
        title="Network Trafik Logları",
        description="Yakalanan XHR, Fetch ve Media (video/audio) ağ trafiği",
        examples=[
            [{
                "url": "https://example.com/api/data",
                "status": 200,
                "mimeType": "application/json",
                "size": 12345,
                "timestamp": 1706265600.123
            }]
        ]
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
