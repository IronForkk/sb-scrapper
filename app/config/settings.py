"""
Konfigürasyon Yönetimi
Ayarları .env dosyasından okur

YASAKLI AYARLAR (Kaldırıldı):
- Rate limiting (intranet uygulaması)
- CORS (intranet uygulaması)
- Authentication (intranet uygulaması)
- Response caching (gereksiz karmaşıklık)
- Task queue (senkron çalışma)
- Monitor (senkron çalışma)
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationError, BeforeValidator
from typing import Annotated, Callable
import sys

from app.config.validators import parse_comma_separated_list


class Settings(BaseSettings):
    # Tarayıcı Ayarları
    headless: bool = Field(default=True, alias="HEADLESS")
    wait_time: int = Field(default=8, alias="WAIT_TIME")
    user_agent_platform: str = Field(default="windows", alias="USER_AGENT_PLATFORM")
    page_load_timeout: int = Field(default=60, alias="PAGE_LOAD_TIMEOUT")
    body_check_wait_time: int = Field(default=2, alias="BODY_CHECK_WAIT_TIME")
    page_reload_wait_time: int = Field(default=5, alias="PAGE_RELOAD_WAIT_TIME")
    
    # ==================== EK BEKLEME SÜRELERİ ====================
    # Mobil mod bekleme süresi (saniye)
    mobile_wait_time: int = Field(default=2, alias="MOBILE_WAIT_TIME")
    
    # Arama motoru bekleme süresi (saniye)
    search_engine_wait_time: int = Field(default=3, alias="SEARCH_ENGINE_WAIT_TIME")
    
    # Frame switch bekleme süresi (saniye)
    frame_switch_wait_time: int = Field(default=1, alias="FRAME_SWITCH_WAIT_TIME")
    
    # Consent tıklama bekleme süresi (saniye)
    consent_click_wait_time: int = Field(default=3, alias="CONSENT_CLICK_WAIT_TIME")

    # API Ayarları
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Loglama Ayarları
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    console_logging_enabled: bool = Field(default=True, alias="CONSOLE_LOGGING_ENABLED")
    postgres_logging_enabled: bool = Field(default=True, alias="POSTGRES_LOGGING_ENABLED")
    structured_logging_enabled: bool = Field(default=False, alias="STRUCTURED_LOGGING_ENABLED")
    gunicorn_logging_enabled: bool = Field(default=True, alias="GUNICORN_LOGGING_ENABLED")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        alias="LOG_FORMAT"
    )

    # Canvas Noise Ayarları
    noise_min_value: int = Field(default=-20, alias="NOISE_MIN_VALUE")
    noise_max_value: int = Field(default=20, alias="NOISE_MAX_VALUE")

    # Black-List Ayarları
    blacklist_file: str = Field(default="black-list.lst", alias="BLACKLIST_FILE")

    # PostgreSQL Ayarları
    postgres_host: str = Field(default="pgbouncer", alias="POSTGRES_HOST")
    # Default port PgBouncer portu ile tutarlı (6432)
    postgres_port: int = Field(default=6432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="sb_scrapper", alias="POSTGRES_DB")
    postgres_user: str = Field(default="sb_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    
    # Request Logging Ayarları
    log_request_body: bool = Field(default=True, alias="LOG_REQUEST_BODY")
    log_request_headers: bool = Field(default=True, alias="LOG_REQUEST_HEADERS")
    log_request_query: bool = Field(default=True, alias="LOG_REQUEST_QUERY")
    
    # Request Log Sınırlamaları
    max_request_body_size: int = Field(default=10240, alias="MAX_REQUEST_BODY_SIZE")  # 10KB
    sensitive_headers: Annotated[
        list[str],
        BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default=[
            # Authentication headers
            "authorization", "proxy-authorization", "www-authenticate",
            # Cookie headers
            "cookie", "set-cookie", "cookie2",
            # API key headers
            "x-api-key", "x-auth-token", "x-access-token", "x-secret",
            # Token headers
            "token", "access-token", "refresh-token", "auth-token",
            # Session headers
            "session-id", "session-token", "session-key",
            # Security headers
            "csrf-token", "x-csrf-token", "x-xsrf-token",
            # Other sensitive headers
            "password", "passwd", "secret", "private-key"
        ],
        alias="SENSITIVE_HEADERS"
    )

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if v.upper() not in valid_levels:
            raise ValueError(f'Geçersiz log seviyesi: {v}')
        return v.upper()

    @field_validator('user_agent_platform')
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ['windows', 'macos', 'linux']
        if v.lower() not in valid_platforms:
            raise ValueError(f'Geçersiz platform: {v}')
        return v.lower()

    @field_validator('wait_time')
    @classmethod
    def validate_wait_time(cls, v):
        if v < 1 or v > 300:
            raise ValueError(f'Geçersiz bekleme süresi: {v}. Değer 1-300 saniye arasında olmalı.')
        return v

    @field_validator('page_load_timeout')
    @classmethod
    def validate_page_load_timeout(cls, v):
        if v < 10 or v > 600:
            raise ValueError(f'Geçersiz sayfa yükleme zaman aşımı: {v}. Değer 10-600 saniye arasında olmalı.')
        return v

    @field_validator('body_check_wait_time')
    @classmethod
    def validate_body_check_wait_time(cls, v):
        if v < 1 or v > 10:
            raise ValueError(f'Geçersiz body kontrol bekleme süresi: {v}. Değer 1-10 saniye arasında olmalı.')
        return v

    @field_validator('page_reload_wait_time')
    @classmethod
    def validate_page_reload_wait_time(cls, v):
        if v < 1 or v > 30:
            raise ValueError(f'Geçersiz sayfa yeniden yükleme bekleme süresi: {v}. Değer 1-30 saniye arasında olmalı.')
        return v
    
    @field_validator('mobile_wait_time')
    @classmethod
    def validate_mobile_wait_time(cls, v):
        if v < 1 or v > 10:
            raise ValueError(f'Geçersiz mobil bekleme süresi: {v}. Değer 1-10 saniye arasında olmalı.')
        return v
    
    @field_validator('search_engine_wait_time')
    @classmethod
    def validate_search_engine_wait_time(cls, v):
        if v < 1 or v > 30:
            raise ValueError(f'Geçersiz arama motoru bekleme süresi: {v}. Değer 1-30 saniye arasında olmalı.')
        return v
    
    @field_validator('frame_switch_wait_time')
    @classmethod
    def validate_frame_switch_wait_time(cls, v):
        if v < 0 or v > 5:
            raise ValueError(f'Geçersiz frame switch bekleme süresi: {v}. Değer 0-5 saniye arasında olmalı.')
        return v
    
    @field_validator('consent_click_wait_time')
    @classmethod
    def validate_consent_click_wait_time(cls, v):
        if v < 1 or v > 10:
            raise ValueError(f'Geçersiz consent tıklama bekleme süresi: {v}. Değer 1-10 saniye arasında olmalı.')
        return v

    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError(f'Geçersiz port numarası: {v}. Değer 1024-65535 arasında olmalı.')
        return v

    @field_validator('noise_min_value', 'noise_max_value')
    @classmethod
    def validate_noise_values(cls, v):
        if v < -50 or v > 50:
            raise ValueError(f'Geçersiz noise değeri: {v}. Değer -50 ile 50 arasında olmalı.')
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


# Settings instance'ını oluştur ve validation hatalarını yakala
try:
    settings = Settings()
except ValidationError as e:
    print("❌ Konfigürasyon hatası tespit edildi!", file=sys.stderr)
    print("\nDetaylı hata bilgisi:", file=sys.stderr)
    for error in e.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        print(f"  - {field}: {message}", file=sys.stderr)
    print("\nLütfen .env dosyanızı kontrol edin ve düzeltin.", file=sys.stderr)
    print("Daha fazla bilgi için .env.example dosyasına bakabilirsiniz.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Beklenmeyen konfigürasyon hatası: {e}", file=sys.stderr)
    sys.exit(1)

