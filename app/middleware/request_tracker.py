"""
Request Tracker Middleware
Gelen isteklerin detaylı bilgilerini PostgreSQL'te loglar
Request ve response bilgileri loglanır (response body hariç)
"""
from typing import Dict, Any
from fastapi import Request, Response
import json
import time
from app.config import settings
from app.core.postgres_logger import postgres_logger


# HTTP method constants
HTTP_METHODS_WITH_BODY = ("POST", "PUT", "PATCH")
FILTERED_HEADER_VALUE = "***FILTERED***"
TRUNCATED_BODY_SUFFIX = "... [TRUNCATED]"
BODY_ERROR_MESSAGE = "Body okunamadı"


def _filter_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Hassas header'ları filtrele
    
    Args:
        headers: Tüm headers
        
    Returns:
        Filtrelenmiş headers
    """
    filtered = {}
    sensitive_lower = [h.lower() for h in settings.sensitive_headers]
    
    for key, value in headers.items():
        if key.lower() not in sensitive_lower:
            filtered[key] = value
        else:
            filtered[key] = FILTERED_HEADER_VALUE
    
    return filtered


def _truncate_body(body: Any, max_size: int) -> Any:
    """
    Request body'yi truncate et
    
    Args:
        body: Request body
        max_size: Maksimum boyut
        
    Returns:
        Truncate edilmiş body
    """
    if body is None:
        return None
    
    body_str = json.dumps(body) if isinstance(body, (dict, list)) else str(body)
    
    if len(body_str) > max_size:
        return body_str[:max_size] + TRUNCATED_BODY_SUFFIX
    
    return body


async def request_tracker_middleware(request: Request, call_next: Any) -> Response:
    """
    Her isteği detaylı şekilde loglar
    
    Loglanan bilgiler:
    Request:
    - IP, Port
    - Method, Path
    - Headers (sensitive'ler filtrelenmiş)
    - Query Parameters
    - Request Body (truncate edilmiş)
    - User Agent
    
    Response:
    - Status Code
    - Response Time (ms)
    - Response Body LOGLANMAZ (güvenlik ve performans için)
    
    Args:
        request: FastAPI Request nesnesi
        call_next: Sonraki middleware/endpoint fonksiyonu
    
    Returns:
        Response: HTTP yanıtı
    """
    # Başlangıç zamanı (response süresi için)
    start_time = time.time()
    
    # İstemci bilgisini al
    client_host = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else 0
    
    # Request bilgilerini topla
    request_data: Dict[str, Any] = {
        "ip": client_host,
        "port": client_port,
        "method": request.method,
        "path": request.url.path,
        "full_url": str(request.url),
    }
    
    # Headers logla
    if settings.log_request_headers:
        headers_dict = dict(request.headers)
        request_data["headers"] = _filter_sensitive_headers(headers_dict)
    
    # Query params logla
    if settings.log_request_query and request.query_params:
        request_data["query_params"] = dict(request.query_params)
    
    # User Agent
    user_agent = request.headers.get("user-agent", None)
    if user_agent:
        request_data["user_agent"] = user_agent
    
    # Request body logla (POST/PUT/PATCH için)
    # Body cache'leme: request.state'de sakla (endpoint'te tekrar okunabilsin)
    if settings.log_request_body and request.method in HTTP_METHODS_WITH_BODY:
        try:
            # Body'yi oku ve cache'le
            body = await request.body()
            
            # Body'yi request.state'de sakla (endpoint'te tekrar okunabilsin)
            request.state._cached_body = body
            
            if body:
                # JSON parse etmeye çalış
                try:
                    body_json = json.loads(body.decode())
                    request_data["body"] = _truncate_body(body_json, settings.max_request_body_size)
                except json.JSONDecodeError:
                    # JSON değilse string olarak kaydet
                    body_str = body.decode()
                    request_data["body"] = _truncate_body(body_str, settings.max_request_body_size)
        except Exception as e:
            # Body okunamazsa hata logla ama devam et
            request_data["body_error"] = BODY_ERROR_MESSAGE
    
    # İsteği işle
    try:
        response = await call_next(request)
        
        # Response bilgilerini ekle
        request_data["response_status_code"] = response.status_code
        request_data["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        # İsteği PostgreSQL'e logla (async olarak)
        await postgres_logger.log_request(request_data)
    finally:
        # Cache'i temizle - Memory leak önlemek için (exception durumunda da çalışır)
        if hasattr(request.state, '_cached_body'):
            delattr(request.state, '_cached_body')
    
    return response


def get_request_context() -> Dict[str, Any]:
    """
    Mevcut request context'ini al (endpoint'ten çağrılır)
    
    Bu fonksiyon, middleware'de toplanan request verilerine erişmek için kullanılır.
    Ancak, FastAPI'de request context'i doğrudan almak için Request dependency kullanılmalıdır.
    
    Returns:
        Dict[str, Any]: Request context bilgisi (şu an için boş dict)
    
    Note:
        Bu fonksiyon gelecekte request state'den veri almak için kullanılabilir.
        Şu an için analyze endpoint'i kendi request verilerini kullanıyor.
    """
    return {}
