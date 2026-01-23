"""
Konfigürasyon Yönetimi
Ayarları .env dosyasından okur
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Tarayıcı Ayarları
    headless: bool = Field(default=True, alias="HEADLESS")
    wait_time: int = Field(default=8, alias="WAIT_TIME")
    user_agent_platform: str = Field(default="windows", alias="USER_AGENT_PLATFORM")

    # API Ayarları
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Loglama Ayarları
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_info_file: str = Field(default="info.log", alias="LOG_INFO_FILE")
    log_error_file: str = Field(default="error.log", alias="LOG_ERROR_FILE")

    # Black-List Ayarları
    blacklist_file: str = Field(default="black-list.lst", alias="BLACKLIST_FILE")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()
