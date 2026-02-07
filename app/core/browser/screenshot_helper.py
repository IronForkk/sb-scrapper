"""
Screenshot Helper Sınıfı
Ekran görüntüsü ve HTML alma işlemleri
"""
import base64
from typing import Any


class ScreenshotHelper:
    """
    Screenshot helper sınıfı
    Ekran görüntüsü ve HTML alma işlemlerini yönetir
    """
    
    def __init__(self, driver: Any):
        """
        Screenshot helper başlat
        
        Args:
            driver: SeleniumBase driver instance
        """
        self.driver = driver
    
    def get_b64_screenshot(self) -> str:
        """
        Ekran görüntüsünü base64 formatında döndürür

        Returns:
            Base64 encoded screenshot
        
        Raises:
            Exception: Screenshot alma hatası
        """
        return self.driver.get_screenshot_as_base64()
    
    def get_b64_html(self) -> str:
        """
        Sayfa kaynağını base64 formatında döndürür

        Returns:
            Base64 encoded HTML
        
        Raises:
            Exception: HTML alma hatası
        """
        src = self.driver.page_source
        return base64.b64encode(src.encode('utf-8')).decode('utf-8')
