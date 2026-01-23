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
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema
