"""
Pydantic Request Şeması
Web Scraping İstek Şeması
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from urllib.parse import urlparse


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
    
    # ==================== NETWORK TRAFİĞİ ====================
    capture_network_logs: bool = Field(
        False,
        title="Ağ Trafiğini Yakala",
        description="XHR, Fetch ve Media (video/audio) ağ trafiğini yakalar. Varsayılan olarak kapalıdır.",
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
        """
        URL validasyonu - Geliştirilmiş versiyon (Hata #6 düzeltmesi)
        
        SSRF (Server-Side Request Forgery) koruması dahildir.
        """
        if not v:
            raise ValueError('URL boş olamaz')
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        
        # Daha kapsamlı URL validasyonu
        parsed = urlparse(v)
        if not parsed.netloc or '.' not in parsed.netloc:
            raise ValueError('Geçersiz URL formatı')
        
        # Protokol kontrolü
        if parsed.scheme not in ('http', 'https'):
            raise ValueError('Sadece HTTP ve HTTPS protokolleri desteklenir')
        
        # SSRF koruması - localhost, 127.0.0.1, 0.0.0.0, ::1 gibi özel IP'leri engelle
        hostname = parsed.netloc.split(':')[0].lower()
        blocked_hosts = [
            'localhost', '127.0.0.1', '0.0.0.0', '::1',
            '169.254.169.254',  # Link-local
            '[::1]', '[::ffff:7f00:1]'  # IPv6 localhost
        ]
        
        if hostname in blocked_hosts:
            raise ValueError(f'Geçersiz URL: {hostname} engellenmiş')
        
        # Özel IP aralıklarını kontrol et (private IP'ler)
        import ipaddress
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private:
                raise ValueError(f'Geçersiz URL: Özel IP adresi engellenmiş')
        except ValueError:
            pass  # IP değilse, domain olarak kabul et
        
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
                    "capture_network_logs": False,
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
                    "capture_network_logs": True,
                    "force_refresh": True
                }
            ]
        }
    }
