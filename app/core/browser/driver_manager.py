"""
Driver Manager Sınıfı
SeleniumBase driver başlatma ve kapatma işlemleri
"""
from seleniumbase import Driver
import json
import platform
import subprocess
import random
from typing import Any

from app.config import settings
from app.core.logger import logger
from app.utils.user_agents import get_random_user_agent
from app.payloads.noise_js import get_consistent_noise_js


class DriverManager:
    """
    SeleniumBase driver yöneticisi
    Driver başlatma, kapatma ve restart işlemlerini yönetir
    """
    
    def __init__(self):
        """Driver manager başlat"""
        self.driver = None
        self.user_agent = get_random_user_agent(platform=settings.user_agent_platform)
        self.noise_r = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_g = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_b = random.randint(settings.noise_min_value, settings.noise_max_value)
    
    def _kill_chrome_processes(self) -> None:
        """
        Platform bağımsız Chrome process kill fonksiyonu
        Windows ve Linux/macOS için farklı komutlar kullanır
        
        Raises:
            Exception: Process kill hatası
        """
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], shell=True, capture_output=True)
                subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], shell=True, capture_output=True)
            else:
                import os
                os.system("pkill -9 -f chrome")
                os.system("pkill -9 -f chromedriver")
        except Exception as e:
            logger.debug(f"Process kill hatası: {e}")
    
    def start_driver(self) -> None:
        """
        Yeni bir tarayıcı sürücüsü başlatır
        
        Raises:
            Exception: Tarayıcı başlatma hatası
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        
        self._kill_chrome_processes()

        logger.info("🔥 Tarayıcı Başlatılıyor...")
        logger.info(f"🌐 User Agent: {self.user_agent[:50]}...")
        
        # Capabilities string ile performance loglarını etkinleştir
        caps = {
            "goog:loggingPrefs": {"performance": "ALL"}
        }
        
        # Chrome argümanları - Headless modda stabil çalışma için gerekli
        chrome_args = [
            "--log-level=0",
            "--disable-logging",
            "--no-sandbox",  # Container'da sandbox modu sorun çıkarabilir
            "--disable-dev-shm-usage",  # /dev/shm kullanımını devre dışı bırak (memory sorunu)
            "--disable-gpu",  # GPU rendering'i devre dışı bırak (headless modda)
            "--disable-software-rasterizer",  # Software rasterizer'ı devre dışı bırak
            "--disable-extensions",  # Extension'ları devre dışı bırak
            "--disable-infobars",  # Info bar'ları devre dışı bırak
            "--disable-notifications",  # Bildirimleri devre dışı bırak
            "--disable-popup-blocking",  # Popup blocking'i devre dışı bırak
            "--disable-blink-features=AutomationControlled",  # Automation detection'i devre dışı bırak
            "--disable-features=IsolateOrigins,site-per-process",  # Site isolation'ı devre dışı bırak (memory)
            "--remote-debugging-port=9222",  # Remote debugging portu
            "--disable-background-timer-throttling",  # Background timer throttling'i devre dışı bırak
            "--disable-backgrounding-occluded-windows",  # Backgrounding occluded windows'ı devre dışı bırak
            "--disable-renderer-backgrounding",  # Renderer backgrounding'i devre dışı bırak
            "--disable-ipc-flooding-protection",  # IPC flooding protection'ı devre dışı bırak
        ]
        
        self.driver = Driver(
            uc=True,
            headless=settings.headless,
            incognito=True,
            agent=self.user_agent,
            cap_string=json.dumps(caps),
            chromium_arg=" ".join(chrome_args)
        )
        self.driver.set_page_load_timeout(settings.page_load_timeout)
        
        # Garanti olması için CDP komutlarını gönder
        try:
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.driver.execute_cdp_cmd('Performance.enable', {})
            logger.info("✅ Performance logları CDP ile etkinleştirildi")
        except Exception as e:
            logger.warning(f"⚠️ CDP log etkinleştirme uyarısı: {str(e)}")

        # JS Buffer'ını Genişlet (Plan B için - KRİTİK ADIM)
        # Normalde tarayıcı sadece 150-250 istek tutar, bunu artırıyoruz.
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "performance.setResourceTimingBufferSize(10000);"
            })
            logger.info("✅ JS Performance buffer genişletildi (10000)")
        except Exception as e:
            logger.warning(f"⚠️ JS buffer genişletme uyarısı: {str(e)}")
        
        # Tarayıcı başlangıcında da buffer genişlet (Hata #5 düzeltmesi)
        try:
            self.driver.execute_script("performance.setResourceTimingBufferSize(10000);")
            logger.info("✅ JS Performance buffer başlangıçta genişletildi (10000)")
        except Exception as e:
            logger.warning(f"⚠️ JS buffer başlangıç genişletme uyarısı: {str(e)}")
        
        # ========================================
        # ANTI-DETECTION KURULUMU
        # ========================================
        # AntiDetection sınıfı üzerinden yap
        from app.core.browser.anti_detection import AntiDetection
        
        anti_detection = AntiDetection(self.driver)
        anti_detection.setup_anti_detection(
            user_agent=self.user_agent,
            noise_r=self.noise_r,
            noise_g=self.noise_g,
            noise_b=self.noise_b
        )
    
    def restart(self) -> None:
        """
        Tarayıcıyı yeniden başlatır
        
        Raises:
            Exception: Tarayıcı başlatma hatası
        """
        logger.warning("Tarayıcı resetleniyor")
        # Noise değerlerini yenile - Config'den okunur
        self.noise_r = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_g = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_b = random.randint(settings.noise_min_value, settings.noise_max_value)
        
        # User Agent'ı yenile (Hata #9 düzeltmesi - platform parametresi eklendi)
        self.user_agent = get_random_user_agent(platform=settings.user_agent_platform)
        logger.info(f"🌐 Yeni User Agent: {self.user_agent[:50]}...")
        
        self.start_driver()
    
    def quit(self) -> None:
        """
        Driver'ı güvenli şekilde kapatır
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔌 Driver kapatıldı")
            except Exception as e:
                logger.warning(f"Driver kapatma hatası: {e}")
        self.driver = None
