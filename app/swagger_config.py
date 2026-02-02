"""
Swagger UI Özelleştirme Ayarları
"""
from fastapi.openapi.utils import get_openapi


def custom_openapi(app):
    """
    Özel OpenAPI şeması oluşturucu
    
    Args:
        app: FastAPI uygulaması
    
    Returns:
        OpenAPI şema sözlüğü
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    
    # Sunucu bilgileri
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Geliştirme ortamı"
        },
        {
            "url": "https://api.example.com",
            "description": "Üretim ortamı"
        }
    ]
    
    # Bileşenler
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API anahtarı (isteğe bağlı)"
        }
    }
    
    # Global güvenlik
    # openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    # Example responses ekle
    openapi_schema["components"]["examples"] = {
        "ScrapeResponseSuccess": {
            "summary": "Başarılı scraping yanıtı",
            "value": {
                "status": "success",
                "raw_desktop_ss": "iVBORw0KGgoAAAANSUhEUgAA...",
                "raw_mobile_ss": "iVBORw0KGgoAAAANSUhEUgAA...",
                "main_desktop_ss": "iVBORw0KGgoAAAANSUhEUgAA...",
                "google_ss": "iVBORw0KGgoAAAANSUhEUgAA...",
                "ddg_ss": "iVBORw0KGgoAAAANSUhEUgAA...",
                "raw_html": "<!DOCTYPE html><html>...</html>",
                "google_html": "<!DOCTYPE html><html>...</html>",
                "ddg_html": "<!DOCTYPE html><html>...</html>",
                "logs": ["🔍 Sayfa yüklendi", "📸 Ekran görüntüsü alındı"],
                "duration": 5.23
            }
        },
        "ScrapeResponseBlacklisted": {
            "summary": "Kara listeye alınmış domain yanıtı",
            "value": {
                "status": "blacklisted",
                "blacklisted_domain": "example.com"
            }
        },
        "ErrorResponse": {
            "summary": "Hata yanıtı",
            "value": {
                "error_code": "BROWSER_BUSY",
                "message": "Tarayıcı şu an meşgul",
                "details": "Lütfen daha sonra tekrar deneyin"
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema
