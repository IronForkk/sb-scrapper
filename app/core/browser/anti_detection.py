"""
Anti-Detection Sınıfı
WebDriver tespit gizleme işlemleri
"""
from typing import Any
from app.config import settings
from app.payloads.noise_js import get_consistent_noise_js
from app.core.logger import loguru_logger as logger


class AntiDetection:
    """
    Anti-detection sınıfı
    WebDriver tespit gizleme işlemlerini yönetir
    """
    
    def __init__(self, driver: Any):
        """
        Anti-detection başlat
        
        Args:
            driver: SeleniumBase driver instance
        """
        self.driver = driver
    
    def setup_anti_detection(self, user_agent: str, noise_r: int, noise_g: int, noise_b: int) -> None:
        """
        Anti-detection kurulumunu yapar
        
        WebDriver tespit gizleme, navigator manipülasyonu,
        canvas noise enjeksiyonu ve user agent rotasyonu içerir.
        
        Args:
            user_agent: User agent string
            noise_r: Kırmızı noise değeri
            noise_g: Yeşil noise değeri
            noise_b: Mavi noise değeri
        
        Raises:
            Exception: Anti-detection kurulum hatası
        """
        # ========================================
        # 0. USER AGENT ROTASYONU
        # ========================================
        try:
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": user_agent
            })
            logger.info("✅ User Agent ayarlandı")
        except Exception as e:
            logger.warning(f"⚠️ User Agent ayarlanamadı: {str(e)}")
        
        # ========================================
        # 1. WEBDRIVER TESPİTİNİ GİZLE
        # ========================================
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            })
            logger.debug("✅ WebDriver tespiti gizlendi")
        except Exception as e:
            logger.warning(f"⚠️ WebDriver gizleme uyarısı: {str(e)}")
        
        # ========================================
        # 2. KAPSAMLI NAVIGATOR API MANİPÜLASYONU
        # ========================================
        navigator_js = """
        (() => {
            // Navigator properties
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
            
            // Chrome object - gerçek Chrome tarayıcı gibi görün
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Permissions API
            if (navigator.permissions && navigator.permissions.query) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }
            
            // Headless detection bypass
            Object.defineProperty(navigator, 'headless', {get: () => false});
            
            // Automation detection bypass - Selenium'in eklediği değişkenleri sil
            delete navigator.__proto__.webdriver;
            delete Object.getPrototypeOf(navigator).webdriver;
            
            // SeleniumBase detection bypass
            const seleniumVars = ['cdc_adoQpoasnfaobpdlhifofobeig', 'cdc_adoQpoasnfaobpdlhifofobeig2'];
            seleniumVars.forEach(v => {
                if (window[v]) delete window[v];
            });
            
            // Connection API
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false
                })
            });
            
            // Battery API (kullanılmıyor ama tespit için)
            if (navigator.getBattery) {
                Object.defineProperty(navigator, 'getBattery', {value: undefined});
            }
            
        })();
        """
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": navigator_js
            })
            logger.debug("✅ Navigator API manipülasyonu yapıldı")
        except Exception as e:
            logger.warning(f"⚠️ Navigator manipülasyon uyarısı: {str(e)}")
        
        # ========================================
        # 3. CANVAS NOISE EKLE
        # ========================================
        noise_js = get_consistent_noise_js(noise_r, noise_g, noise_b)
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": noise_js
            })
            logger.debug(f"✅ Canvas noise eklendi (R:{noise_r}, G:{noise_g}, B:{noise_b})")
        except Exception as e:
            logger.warning(f"⚠️ Canvas noise ekleme uyarısı: {str(e)}")
