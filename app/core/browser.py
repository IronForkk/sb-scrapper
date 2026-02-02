"""
Browser Manager Sınıfı
SeleniumBase ile tarayıcı yönetimi

Thread-safe singleton pattern
"""
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time, os
import threading
import base64
import random
import json
import platform
import subprocess
import glob
from typing import Any, Optional, Dict, List
from fastapi import HTTPException
from urllib.parse import quote, urlparse

# Memory Profiler import (opsiyonel)
try:
    from memory_profiler import profile
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    # Dummy decorator
    def profile(func=None, precision=None, stream=None, backend=None):
        if func is None:
            return lambda f: f
        return func

from app.config import settings
from app.core.logger import logger
from app.core.blacklist import BlacklistManager
from app.payloads.noise_js import get_consistent_noise_js
from app.payloads.sentinel_js import JS_SENTINEL
from app.schemas import ScrapeRequest, ScrapeResponse
from app.utils.user_agents import get_random_user_agent


# Black-List Manager Singleton
blacklist_mgr = BlacklistManager(settings.blacklist_file)
logger.info(f"🚫 Black-list yüklendi: {blacklist_mgr.get_blacklist_count()} domain")


class BrowserManager:
    """
    SeleniumBase tabanlı tarayıcı yöneticisi
    Thread-safe singleton pattern (Double-Checked Locking)
    """
    
    _instance = None
    _class_lock = threading.Lock()
    _initialized = False  # Sınıf seviyesinde initialized bayrağı
    
    def __new__(cls):
        """Thread-safe singleton pattern (Double-Checked Locking)"""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._initialized = False  # İlk oluşturmada False yap
        return cls._instance

    def __init__(self):
        # Thread-safe singleton - sadece bir kez çalışmalı
        if BrowserManager._initialized:
            return
        with BrowserManager._class_lock:
            if BrowserManager._initialized:
                return
            BrowserManager._initialized = True
        
        self.driver = None
        self.lock = threading.Lock()
        
        # Rastgele noise değerleri (her oturum için tutarlı) - Config'den okunur
        self.noise_r = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_g = random.randint(settings.noise_min_value, settings.noise_max_value)
        self.noise_b = random.randint(settings.noise_min_value, settings.noise_max_value)
        
        # Rastgele User Agent
        self.user_agent = get_random_user_agent(platform=settings.user_agent_platform)
        
        self.start_driver()

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
        
        self.driver = Driver(
            uc=True,
            headless=settings.headless,
            incognito=True,
            agent=self.user_agent,
            cap_string=json.dumps(caps),
            chromium_arg="--log-level=0 --disable-logging"
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
        # 0. USER AGENT ROTASYONU
        # ========================================
        try:
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": self.user_agent
            })
            logger.info("✅ User Agent ayarlandı")
        except Exception as e:
            logger.warning(f"⚠️ User Agent ayarlanamadı: {str(e)}")
        
        # ========================================
        # 1. WEBDRIVER TESPİTİNİ GİZLE
        # ========================================
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        })
        
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
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": navigator_js
        })
        
        # ========================================
        # 3. CANVAS NOISE EKLE
        # ========================================
        noise_js = get_consistent_noise_js(self.noise_r, self.noise_g, self.noise_b)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": noise_js
        })

    def _clear_driver_logs(self) -> None:
        """
        Driver loglarını ve CDP buffer'ını tamamen temizle.
        
        Bu metod HAYATİ ÖNEM TAŞIYOR çünkü:
        1. CDP Network.enable çok veri üretir
        2. Performance logları biriktikçe RAM şişer
        3. JS Performance buffer da dolabilir
        4. Her scrape sonrası TEMİZLENMELİDİR
        
        Not: Chrome 144+ sürümleri "performance" log tipini desteklemiyor.
        Bu yüzden sadece JS Performance API kullanılıyor.
        
        Raises:
            Exception: Log temizleme hatası
        """
        # --- YÖNTEM 1: CDP Loglarını Temizle (KRİTİK) ---
        # CDP buffer'ını temizle - Network.enable çok veri üretir!
        # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
        try:
            # Performance loglarını al (ve böylece temizle)
            # Iterasyon sayısı artırıldı (10 -> 50) - daha agresif temizleme
            max_iterations = 50
            iteration = 0
            total_logs_cleared = 0
            while iteration < max_iterations:
                logs = self.driver.get_log("performance")
                if not logs:
                    break
                total_logs_cleared += len(logs)
                iteration += 1
            logger.debug(f"CDP Performance logları temizlendi ({iteration} iterasyon, {total_logs_cleared} log)")
        except Exception as e:
            # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
            # Bu durumda JS Performance API kullanılıyor
            logger.debug(f"CDP log temizleme başarısız (Chrome 144+), JS buffer temizleniyor: {str(e)}")

        # --- YÖNTEM 2: JS Performance Buffer'ı Temizle ---
        try:
            # Resource timing buffer'ı temizle
            self.driver.execute_script("performance.clearResourceTimings();")

            # Memory buffer'ı temizle
            self.driver.execute_script("performance.clearMarks();")
            self.driver.execute_script("performance.clearMeasures();")

            # Agresif memory cleanup - JS garbage collection tetikle
            self.driver.execute_script("""
                // Resource timings'ı temizle
                if (performance.clearResourceTimings) {
                    performance.clearResourceTimings();
                }
                
                // Marks ve measures'ı temizle
                if (performance.clearMarks) {
                    performance.clearMarks();
                }
                
                if (performance.clearMeasures) {
                    performance.clearMeasures();
                }
                
                // Memory cleanup - Garbage collection tetikle
                if (window.gc) {
                    window.gc();
                }
                
                // DOM cache temizle
                if (window.performance && window.performance.memory) {
                    // Chrome DevTools Performance API memory cleanup
                    const memory = window.performance.memory;
                    if (memory && memory.usedJSHeapSize) {
                        // Force memory cleanup
                        console.log('Memory cleanup triggered');
                    }
                }
            """)

            logger.debug("JS Performance buffer ve memory temizlendi")
        except Exception as e:
            logger.warning(f"JS buffer temizleme hatası: {str(e)}")

    def cleanup_temp_files(self) -> None:
        """
        /tmp içindeki Chrome geçici dosyalarını temizle
        
        Bu metod:
        1. Chrome geçici dosyalarını bulur
        2. Logları temizler
        3. _clear_driver_logs() çağırır
        """
        try:
            # Platform bağımsız /tmp yolu
            if platform.system() == "Windows":
                import os
                tmp_path = os.environ.get('TEMP', 'C:\\Temp')
                chrome_pattern = os.path.join(tmp_path, 'chrome_*')
            else:
                tmp_path = '/tmp'
                chrome_pattern = '/tmp/chrome_*'
            
            # Chrome geçici dizinlerini bul
            chrome_dirs = glob.glob(chrome_pattern)
            
            if chrome_dirs:
                logger.info(f"🧹 {len(chrome_dirs)} adet Chrome geçici dizini temizleniyor...")
                for chrome_dir in chrome_dirs:
                    try:
                        shutil.rmtree(chrome_dir)
                        logger.debug(f"Temizlendi: {chrome_dir}")
                    except Exception as e:
                        logger.debug(f"Temizleme hatası ({chrome_dir}): {e}")
                
                logger.info(f"✅ {len(chrome_dirs)} adet Chrome geçici dizini temizlendi")
            else:
                logger.debug("Temizlenecek Chrome geçici dizini bulunamadı")
            
            # Driver loglarını temizle
            if self.driver:
                self._clear_driver_logs()
            
        except Exception as e:
            logger.error(f"Temp dosya temizleme hatası: {e}")

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

    def human_click(self, element: Any) -> None:
        """
        İnsan benzeri tıklama davranışı

        Args:
            element: Selenium element
        
        Raises:
            Exception: Tıklama hatası
        """
        try:
            action = ActionChains(self.driver)
            action.move_to_element(element).perform()
            time.sleep(random.uniform(0.2, 0.5))
            action.click().perform()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    def _switch_and_click_in_frame(self, frame_selector: str, selectors: list[str], logs: list[str], log_msg: str) -> bool:
        """
        Helper fonksiyon: iframe'e geç ve seçicileri dene
        
        Args:
            frame_selector: iframe CSS seçicisi
            selectors: Denenecek CSS seçicileri listesi
            logs: Log listesi
            log_msg: Başarılı olduğunda eklenecek mesaj
            
        Returns:
            Başarılı ise True, değilse False
        
        Raises:
            Exception: Frame işlemi hatası
        """
        try:
            frames = self.driver.find_elements(By.CSS_SELECTOR, frame_selector)
            if frames:
                self.driver.switch_to.frame(frames[0])
                time.sleep(1)
                for selector in selectors:
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if checkbox.is_displayed():
                            self.human_click(checkbox)
                            logs.append(log_msg)
                            time.sleep(3)
                            return True
                    except Exception:
                        continue
                self.driver.switch_to.default_content()
        except Exception as e:
            logs.append(f"⚠️ Frame işlemi başarısız: {str(e)}")
            self.driver.switch_to.default_content()
        return False

    def solve_captcha_and_consent(self, logs: list[str], is_google: bool = False) -> None:
        """
        Captcha ve consent formlarını otomatik çözer.
        
        Desteklenen Captcha Türleri:
        - Google Consent
        - Cloudflare
        - ReCaptcha
        - Turnstile (YENİ)
        - HCaptcha (YENİ)

        Args:
            logs: Log listesi
            is_google: Google sayfası mı
        
        Raises:
            Exception: Captcha çözme hatası
        """
        try:
            if is_google:
                google_selectors = [
                    "//div[text()='Tümünü kabul et']", "//div[text()='Accept all']",
                    "//*[@id='L2AGLb']", "//*[@id='W0wltc']",
                    "//button[contains(.,'Kabul')]", "//button[contains(.,'Accept')]"
                ]
                for xpath in google_selectors:
                    try:
                        el = self.driver.find_element(By.XPATH, xpath)
                        if el.is_displayed():
                            self.human_click(el)
                            logs.append("✅ Google Çerezi Tıklandı")
                            time.sleep(2)
                            break
                    except Exception:
                        pass

            # Cloudflare
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='cloudflare']")
            if frames:
                logs.append("🛡️ Cloudflare tespit edildi...")
                self.driver.switch_to.frame(frames[0])
                time.sleep(1)
                try:
                    cb = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    self.human_click(cb)
                    logs.append("✅ Cloudflare Checkbox Tıklandı")
                except Exception:
                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        self.human_click(body)
                        logs.append("✅ Cloudflare Gövde Tıklandı")
                    except Exception:
                        pass
                time.sleep(5)
                self.driver.switch_to.default_content()
            
            # ReCaptcha
            frames_re = self.driver.find_elements(By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")
            if frames_re:
                self.driver.switch_to.frame(frames_re[0])
                try:
                    box = self.driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-border")
                    self.human_click(box)
                    logs.append("✅ ReCaptcha Tıklandı")
                    time.sleep(2)
                except Exception:
                    pass
                self.driver.switch_to.default_content()
            
            # Turnstile (YENİ)
            turnstile_selectors = [
                "input[type='checkbox']",
                ".cb-i",
                "[aria-label='Verify you are human']",
                "div[class*='checkbox']"
            ]
            if self._switch_and_click_in_frame("iframe[src*='turnstile']", turnstile_selectors, logs, "✅ Turnstile Checkbox Tıklandı"):
                time.sleep(2)
            
            # HCaptcha (YENİ)
            hcaptcha_selectors = [
                ".h-captcha-checkbox",
                ".hcaptcha-checkbox",
                "input[type='checkbox']",
                "[aria-label='hCaptcha']"
            ]
            if self._switch_and_click_in_frame("iframe[src*='hcaptcha']", hcaptcha_selectors, logs, "✅ HCaptcha Checkbox Tıklandı"):
                time.sleep(2)
                
        except Exception:
            self.driver.switch_to.default_content()

    def smart_wait_and_kill(self, wait_time: int, logs: list[str], mobile_mode: bool = False) -> None:
        """
        Akıllı bekleme ve popup temizleme
 
        Args:
            wait_time: Bekleme süresi (saniye)
            logs: Log listesi
            mobile_mode: Mobil mod mu
        
        Raises:
            Exception: Wait işlemi hatası
        """
        # Nöbetçiyi enjekte et
        try:
            self.driver.execute_script(JS_SENTINEL)
        except Exception:
            pass
        
        steps = 2
        if mobile_mode:
            steps = 3

        for i in range(steps):
            if mobile_mode:
                try:
                    # Scroll Dansı (Popupları tetiklemek için)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(1)
                    
                    # Sayfanın ortasına hayalet tıklama
                    self.driver.execute_script("document.elementFromPoint(window.innerWidth/2, window.innerHeight/2).click();")
                    
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
                    time.sleep(1)
                    self.driver.execute_script("window.scrollTo(0, 0);")
                except Exception:
                    pass
            else:
                time.sleep(wait_time / steps)
            
            try:
                self.driver.execute_script("document.body.style.overflow='visible';")
            except Exception:
                pass

    def _is_relevant_url(self, url: str, mime_type: str) -> bool:
        """
        Helper: Hangi URL'lerin kaydedileceğine karar verir

        Args:
            url: URL string
            mime_type: MIME type string

        Returns:
            True if URL is relevant, False otherwise
        
        Not: Deprecated - _analyze_traffic_type kullanılıyor
        """
        return self._analyze_traffic_type(url, mime_type) != "ignore"

    def _analyze_traffic_type(self, url: str, initiator: str = "") -> str:
        """
        URL ve Çağıran (Initiator) bilgisine bakarak trafiğin amacını belirler.
        
        Args:
            url: URL string
            initiator: Çağıran (initiator type)
        
        Returns:
            'api', 'tracker', 'script' veya 'ignore'
        """
        u = url.lower()
        
        # 1. KESİN REDDEDİLECEKLER (Gürültü)
        # Görsel, Stil, Font, Medya dosyaları
        extensions_to_ignore = [
            '.css', '.woff', '.woff2', '.ttf', '.eot', '.svg', '.png', '.jpg',
            '.jpeg', '.gif', '.ico', '.webp', '.mp4', '.mp3', '.m3u8', '.ts',
            '.pdf', '.zip'
        ]
        if any(u.endswith(ext) or f"{ext}?" in u for ext in extensions_to_ignore):
            return "ignore"

        # 2. API / VERİ TRAFİĞİ (XHR ve Fetch)
        # Genellikle JSON veya XML dönerler
        is_api_keyword = "api" in u or "json" in u or "ajax" in u or "graphql" in u or "v1/" in u
        if initiator in ['xmlhttprequest', 'fetch'] or is_api_keyword:
            return "api"

        # 3. TRACKER / ANALYTICS (Genellikle Script veya Pixel)
        trackers = ['google-analytics', 'facebook', 'pixel', 'gtm', 'stats', 'metrics', 'telemetry']
        if any(t in u for t in trackers):
            return "tracker"

        # 4. HARİCİ SCRIPTLER (CDN'den gelen JS kütüphaneleri veya reklamlar)
        if u.endswith('.js') or '.js?' in u or initiator == 'script':
            return "script"

        # Geri kalanlar (Navigasyon vb.) önemsiz sayılabilir ama
        # API kaçırmamak için şüpheli olarak işaretleyebiliriz.
        return "ignore"

    def _get_network_logs_from_cdp(self) -> list[dict]:
        """
        CDP (Chrome DevTools Protocol) ile network loglarını yakalar.
        Status code, headers, timing gibi detaylı bilgileri içerir.
        
        Not: Chrome 144+ sürümleri "performance" log tipini desteklemiyor.
        Bu durumda JS Performance API fallback kullanılır.
        
        Returns:
            Network logları listesi
        
        Raises:
            Exception: CDP log alma hatası
        """
        try:
            # CDP ile network loglarını al
            logs = self.driver.get_log("performance")
            relevant_logs = []
            
            for entry in logs:
                try:
                    log_json = json.loads(entry["message"])
                    message = log_json["message"]
                    
                    if message["method"] == "Network.responseReceived":
                        params = message["params"]
                        resp = params.get("response", {})
                        url = resp.get("url", "")
                        
                        # Traffic type analizi
                        traffic_type = self._analyze_traffic_type(url, "")
                        
                        if traffic_type != "ignore":
                            relevant_logs.append({
                                "source": "cdp",
                                "type": traffic_type,
                                "domain": url.split('/')[2] if '//' in url else url,
                                "url": url,
                                "status": resp.get("status", 0),
                                "status_text": resp.get("statusText", ""),
                                "mime_type": resp.get("mimeType", ""),
                                "headers": resp.get("headers", {}),
                                "size": resp.get("encodedDataLength", 0),
                                "timing": params.get("timing", {})
                            })
                except Exception:
                    continue
            
            return relevant_logs
        except Exception as e:
            # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
            # Bu durumda JS Performance API fallback kullanılır
            logger.debug(f"CDP log tipi desteklenmiyor (Chrome 144+), JS fallback kullanılıyor: {str(e)}")
            return []

    def capture_network_logs(self) -> list[dict]:
        """
        Sitenin dış dünya ile iletişimini (API, XHR, Tracker) analiz eder.
        Görsel, CSS ve Medya dosyalarını filtreler.
        
        İki yöntem kullanır:
        1. CDP (Chrome DevTools Protocol) - Detaylı bilgiler (status code, headers)
        2. JS Performance API - Fallback
        
        NOT: CDP buffer'ı scrape sonunda _clear_driver_logs() ile temizlenmelidir.
        
        Returns:
            Network logları listesi
        
        Raises:
            Exception: Trafik analizi hatası
        """
        relevant_logs = []
        
        # --- YÖNTEM 1: CDP (Chrome DevTools Protocol) - Detaylı ---
        try:
            cdp_logs = self._get_network_logs_from_cdp()
            if cdp_logs:
                relevant_logs.extend(cdp_logs)
                logger.info(f"✅ CDP ile {len(cdp_logs)} network logu yakalandı.")
        except Exception as e:
            logger.warning(f"⚠️ CDP log alma hatası: {e}")
        
        # --- YÖNTEM 2: JS Performance API (Fallback) ---
        # CDP başarısız olursa veya ek loglar için
        if not relevant_logs:
            try:
                js_script = """
                return performance.getEntriesByType("resource").map(r => ({
                    url: r.name,
                    initiatorType: r.initiatorType,
                    size: r.transferSize || 0,
                    time: r.startTime,
                    duration: r.duration,
                    nextHopProtocol: r.nextHopProtocol
                }));
                """
                js_logs = self.driver.execute_script(js_script)
                
                for log in js_logs:
                    url = log.get("url", "")
                    initiator = log.get("initiatorType", "").lower()
                    
                    traffic_type = self._analyze_traffic_type(url, initiator)
                    
                    if traffic_type != "ignore":
                        domain = url.split('/')[2] if '//' in url else url
                        
                        relevant_logs.append({
                            "source": "js_fallback",
                            "type": traffic_type,
                            "domain": domain,
                            "url": url,
                            "status": None,  # JS API status code vermez
                            "status_text": "N/A",
                            "mime_type": None,
                            "headers": {},
                            "size": log.get("size", 0),
                            "timing": {
                                "start_time": log.get("time", 0),
                                "duration": log.get("duration", 0),
                                "protocol": log.get("nextHopProtocol", "unknown")
                            }
                        })
                
                if relevant_logs:
                    logger.info(f"✅ JS Fallback ile {len(relevant_logs)} network logu yakalandı.")
            
            except Exception as e:
                logger.error(f"❌ Trafik analizi yapılamadı: {e}")
        
        return relevant_logs

    @profile(precision=4, stream=open('memory_profile.log', 'w+'), backend='psutil')
    def process(self, req: ScrapeRequest) -> ScrapeResponse:
        """
        İstemi işler ve yanıt döndürür

        Args:
            req: ScrapeRequest nesnesi

        Returns:
            ScrapeResponse nesnesi
        
        Raises:
            HTTPException: Tarayıcı meşgul ise (429 BUSY)
            Exception: Scrape işlemi hatası
        """
        if not self.lock.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="BUSY")

        try:
            start_time = time.time()
            logs = []
            network_data = []  # Ağ trafiği verisi en başta tanımla
            res = ScrapeResponse(status="processing", logs=[], duration=0)
            
            def log(m: str):
                logs.append(m)
                logger.info(f"[{req.url}] {m}")

            try:
                if req.force_refresh:
                    self.restart()
                
                raw_url = req.url
                if not raw_url.startswith("http"):
                    raw_url = "https://" + raw_url
                parsed = urlparse(raw_url)
                domain = parsed.netloc
                if ':' in domain:
                    domain = domain.split(':')[0]
                main_domain_url = f"https://{domain}"

                # BLACK-LIST KONTROLÜ
                if blacklist_mgr.is_blacklisted(domain):
                    logger.warning(f"🚫 Black-list domain tespit edildi: {domain}")
                    return ScrapeResponse(
                        status="blacklisted",
                        logs=[f"🚫 Domain black-list'te: {domain}"],
                        blacklisted_domain=domain,
                        duration=time.time() - start_time
                    )

                # Sayfa yüklenmeden önce logları temizle (Hata #7 düzeltmesi)
                # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
                # try:
                #     self.driver.get_log("performance")
                # except Exception:
                #     pass
                
                # ADIM 1: HAM URL
                if req.process_raw_url:
                    log(f"Adım 1: Ham URL -> {raw_url}")
                    try:
                        self.driver.get(raw_url)
                    except Exception as e:
                        log("Sayfa yüklenemedi")
                        raise
                    self.solve_captcha_and_consent(logs)
                    self.smart_wait_and_kill(req.wait_time, logs)
                    
                    # Body check - JavaScript yüklenmesi için bekleme
                    time.sleep(settings.body_check_wait_time if hasattr(settings, 'body_check_wait_time') else 2)
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(body_text) < 100:
                        logger.warning("Sayfa içeriği çok az, sayfa yeniden yükleniyor...")
                        self.driver.refresh()
                        time.sleep(settings.page_reload_wait_time if hasattr(settings, 'page_reload_wait_time') else 5)

                    res.raw_desktop_ss = self.get_b64_screenshot()
                    if req.get_html:
                        res.raw_html = self.get_b64_html()
                    
                    # MOBİL - Opsiyonel
                    if req.get_mobile_ss:
                        log(f"Adım 2: 📱 Mobil -> {raw_url}")
                        try:
                            self.driver.execute_cdp_cmd(
                                "Emulation.setDeviceMetricsOverride",
                                {"width": 375, "height": 812, "deviceScaleFactor": 3, "mobile": True}
                            )
                            self.driver.refresh()
                            
                            time.sleep(2)
                            self.solve_captcha_and_consent(logs)
                            self.smart_wait_and_kill(req.wait_time, logs, mobile_mode=True)
                            
                            res.raw_mobile_ss = self.get_b64_screenshot()
                            self.driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
                        except Exception:
                            log("Mobil mod hatası")
                            try:
                                self.driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
                            except Exception:
                                pass
                            raise

                # ADIM 2: ANA DOMAIN
                if req.process_main_domain:
                    if raw_url.rstrip('/') == main_domain_url.rstrip('/'):
                        if res.raw_desktop_ss:
                            res.main_desktop_ss = res.raw_desktop_ss
                        else:
                            log(f"Adım 3: Ana Domain -> {main_domain_url}")
                            self.driver.get(main_domain_url)
                            self.solve_captcha_and_consent(logs)
                            self.smart_wait_and_kill(req.wait_time, logs)
                            res.main_desktop_ss = self.get_b64_screenshot()
                    else:
                        log(f"Adım 3: Ana Domain -> {main_domain_url}")
                        self.driver.get(main_domain_url)
                        self.solve_captcha_and_consent(logs)
                        self.smart_wait_and_kill(req.wait_time, logs)
                        res.main_desktop_ss = self.get_b64_screenshot()
 
                # 🔥 KRİTİK HAMLE: Google'a gitmeden önce AĞ TRAFİĞİNİ YAKALA! 🔥
                if req.capture_network_logs:
                    log("📡 Hedef site trafiği toplanıyor...")
                    network_data = self.capture_network_logs()
                    log(f"✅ {len(network_data)} adet kritik ağ isteği yakalandı.")
                
                # -------------------------------------------------------
                # BURADAN SONRA TARAYICI BAŞKA SİTELERE GİDECEK
                # -------------------------------------------------------

                # ADIM 3: GOOGLE ARAMASI (Opsiyonel)
                if req.get_google_search:
                    log(f"Adım 4: 🔍 Google -> {domain}")
                    safe_domain = quote(domain, safe='')
                    self.driver.get(f"https://www.google.com/search?q=site%3A{safe_domain}")
                    time.sleep(3)
                    self.solve_captcha_and_consent(logs, is_google=True)
                    res.google_ss = self.get_b64_screenshot()
                    if req.get_google_html:
                        res.google_html = self.get_b64_html()

                # ADIM 4: DUCKDUCKGO ARAMASI (Opsiyonel)
                if req.get_ddg_search:
                    log(f"Adım 5: 🦆 DDG -> {domain}")
                    safe_domain = quote(domain, safe='')
                    self.driver.get(f"https://duckduckgo.com/?q=site%3A{safe_domain}")
                    time.sleep(3)
                    res.ddg_ss = self.get_b64_screenshot()
                    if req.get_ddg_html:
                        res.ddg_html = self.get_b64_html()
                
                # Ağ trafiği verisini yanıta ekle
                if req.capture_network_logs:
                    res.network_logs = network_data

                res.status = "success"
                log(f"✅ Bitti -> {domain}")

            except Exception as e:
                log(f"❌ HATA: {str(e)}")
                res.status = "error"
                logger.error(f"Scrape işlemi başarısız: {req.url} - {str(e)}", exc_info=True)
                
                # Zombi process temizleme
                try:
                    self._kill_chrome_processes()
                    logger.info("Zombi Chrome process'leri temizlendi")
                except Exception as cleanup_error:
                    logger.error(f"Zombi temizleme hatası: {cleanup_error}")
                
                self.restart()

            res.logs = logs
            res.duration = time.time() - start_time

            # ========================================
            # 🔥 KRİTİK: Response return edilmeden ÖNCE
            # Driver loglarını tamamen temizle!
            # ========================================
            self._clear_driver_logs()

            return res

        finally:
            self.lock.release()
