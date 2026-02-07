"""
Browser Manager Sınıfı
SeleniumBase ile tarayıcı yönetimi

Basit singleton pattern (senkron)
"""
from typing import Any

from app.config import settings
from app.core.logger import loguru_logger as logger
from app.core.browser.driver_manager import DriverManager
from app.core.browser.memory_cleaner import MemoryCleaner
from app.core.browser.screenshot_helper import ScreenshotHelper
from app.core.browser.popup_handler import PopupHandler
from app.core.browser.network_logger import NetworkLogger
from app.core.browser.scrape_processor import ScrapeProcessor
from app.core.browser.captcha_solver import CaptchaSolver
# AntiDetection import'unu kaldır (artık driver_manager içinde kullanılıyor)
# from app.core.browser.anti_detection import AntiDetection
from app.schemas import ScrapeRequest, ScrapeResponse


class BrowserManager:
    """
    SeleniumBase tabanlı tarayıcı yöneticisi
    Basit singleton pattern (senkron)
    """
    
    _instance = None
    _initialized = False  # Sınıf seviyesinde initialized bayrağı
    
    def __new__(cls):
        """Basit singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialized = False
        return cls._instance

    def __init__(self):
        # Basit singleton - sadece bir kez çalışmalı
        if BrowserManager._initialized:
            return
        
        # Driver manager başlat
        self.driver_manager = DriverManager()
        self.driver = self.driver_manager.driver
        
        # Helper sınıflarını başlat
        self.memory_cleaner = MemoryCleaner(self.driver)
        self.screenshot_helper = ScreenshotHelper(self.driver)
        self.popup_handler = PopupHandler(self.driver)
        self.network_logger = NetworkLogger(self.driver)
        # AntiDetection sınıfı artık driver_manager içinde kullanılıyor
        # self.anti_detection = AntiDetection(self.driver)
        self.captcha_solver = CaptchaSolver(self.popup_handler)
        
        # Scrape processor başlat
        self.scrape_processor = ScrapeProcessor(
            self.driver,
            self.popup_handler,
            self.screenshot_helper,
            self.network_logger
        )
        
        # Son olarak initialized bayrağını ayarla
        BrowserManager._initialized = True
    
    def start_driver(self) -> None:
        """Driver'ı başlat"""
        self.driver_manager.start_driver()
        self.driver = self.driver_manager.driver
        
        # Helper sınıflarını güncelle
        self.memory_cleaner = MemoryCleaner(self.driver)
        self.screenshot_helper = ScreenshotHelper(self.driver)
        self.popup_handler = PopupHandler(self.driver)
        self.network_logger = NetworkLogger(self.driver)
        # AntiDetection artık driver_manager içinde kullanılıyor
        # self.anti_detection = AntiDetection(self.driver)
        self.captcha_solver = CaptchaSolver(self.popup_handler)
        
        # Scrape processor'ı güncelle
        self.scrape_processor = ScrapeProcessor(
            self.driver,
            self.popup_handler,
            self.screenshot_helper,
            self.network_logger
        )
    
    def restart(self) -> None:
        """Tarayıcıyı yeniden başlatır"""
        self.driver_manager.restart()
        self.driver = self.driver_manager.driver
        
        # Helper sınıflarını güncelle
        self.memory_cleaner = MemoryCleaner(self.driver)
        self.screenshot_helper = ScreenshotHelper(self.driver)
        self.popup_handler = PopupHandler(self.driver)
        self.network_logger = NetworkLogger(self.driver)
        # AntiDetection artık driver_manager içinde kullanılıyor
        # self.anti_detection = AntiDetection(self.driver)
        self.captcha_solver = CaptchaSolver(self.popup_handler)
        
        # Scrape processor'ı güncelle
        self.scrape_processor = ScrapeProcessor(
            self.driver,
            self.popup_handler,
            self.screenshot_helper,
            self.network_logger
        )
    
    def cleanup_temp_files(self) -> None:
        """Geçici dosyaları temizler"""
        self.memory_cleaner.cleanup_temp_files()
    
    def _clear_driver_logs(self) -> None:
        """Driver loglarını temizler"""
        self.memory_cleaner._clear_driver_logs()
    
    def process(self, req: ScrapeRequest) -> ScrapeResponse:
        """
        İstemi işler ve yanıt döndürür

        Args:
            req: ScrapeRequest nesnesi

        Returns:
            ScrapeResponse nesnesi
        
        Raises:
            Exception: Scrape işlemi hatası
        """
        # Force refresh kontrolü
        if req.force_refresh:
            self.restart()
        
        # Scrape işlemi
        try:
            res = self.scrape_processor.process(req)
            
            # Response return edilmeden ÖNCE Driver loglarını temizle
            self._clear_driver_logs()
            
            return res
        except Exception as e:
            # Hata durumunda zombi process'leri temizle ve tarayıcıyı restart et
            logger.error(f"Scrape hatası, tarayıcı restart ediliyor: {str(e)}")
            
            # Zombi process temizleme
            try:
                self.driver_manager._kill_chrome_processes()
                logger.info("Zombi Chrome process'leri temizlendi")
            except Exception as cleanup_error:
                logger.error(f"Zombi temizleme hatası: {cleanup_error}")
            
            # Driver restart
            self.restart()
            
            # Hata response'u döndür
            return ScrapeResponse(
                status="error",
                logs=[f"❌ HATA: {str(e)}"],
                duration=0
            )
    
    def quit(self) -> None:
        """Driver'ı kapatır"""
        self.driver_manager.quit()
