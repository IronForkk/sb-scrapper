"""
Browser Manager Sınıfı
SeleniumBase ile tarayıcı yönetimi
"""
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time, os
import threading
import base64
import random
import json
from typing import Any
from fastapi import HTTPException

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
    Thread-safe singleton pattern
    """
    
    _instance = None
    _class_lock = threading.Lock()
    
    def __new__(cls):
        """Thread-safe singleton pattern"""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.driver = None
        self.lock = threading.Lock()
        
        # Rastgele noise değerleri (her oturum için tutarlı) - Genişletilmiş aralık
        self.noise_r = random.randint(-20, 20)
        self.noise_g = random.randint(-20, 20)
        self.noise_b = random.randint(-20, 20)
        
        # Rastgele User Agent
        self.user_agent = get_random_user_agent(platform=settings.user_agent_platform)
        
        self.start_driver()

    def start_driver(self) -> None:
        """
        Yeni bir tarayıcı sürücüsü başlatır
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        
        try:
            os.system("pkill -9 -f chrome")
            os.system("pkill -9 -f chromedriver")
        except Exception as e:
            logger.debug(f"Process kill hatası: {e}")

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
            chromium_arg="--enable-logging --v=1"
        )
        self.driver.set_page_load_timeout(60)
        
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

    def restart(self) -> None:
        """
        Tarayıcıyı yeniden başlatır
        """
        logger.warning("♻️ Tarayıcı Resetleniyor...")
        # Noise değerlerini yenile - Genişletilmiş aralık
        self.noise_r = random.randint(-20, 20)
        self.noise_g = random.randint(-20, 20)
        self.noise_b = random.randint(-20, 20)
        
        # User Agent'ı yenile (Hata #9 düzeltmesi - platform parametresi eklendi)
        self.user_agent = get_random_user_agent(platform=settings.user_agent_platform)
        logger.info(f"🌐 Yeni User Agent: {self.user_agent[:50]}...")
        
        self.start_driver()

    def get_b64_screenshot(self) -> str:
        """
        Ekran görüntüsünü base64 formatında döndürür

        Returns:
            Base64 encoded screenshot
        """
        return self.driver.get_screenshot_as_base64()
    
    def get_b64_html(self) -> str:
        """
        Sayfa kaynağını base64 formatında döndürür

        Returns:
            Base64 encoded HTML
        """
        src = self.driver.page_source
        return base64.b64encode(src.encode('utf-8')).decode('utf-8')

    def human_click(self, element: Any) -> None:
        """
        İnsan benzeri tıklama davranışı

        Args:
            element: Selenium element
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
        """
        """
        Helper fonksiyon: iframe'e geç ve seçicileri dene
        
        Args:
            frame_selector: iframe CSS seçicisi
            selectors: Denenecek CSS seçicileri listesi
            logs: Log listesi
            log_msg: Başarılı olduğunda eklenecek mesaj
            
        Returns:
            Başarılı ise True, değilse False
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
        """
        mime_type = mime_type.lower()
        url_lower = url.lower()
        
        # Google ve DuckDuckGo trafiğini filtrele
        if "google.com" in url_lower or "duckduckgo.com" in url_lower:
            return False
        
        is_xhr = "json" in mime_type or "xml" in mime_type or "api" in url or "ajax" in url
        is_media = ("video" in mime_type or "audio" in mime_type or
                    "stream" in mime_type or ".m3u8" in url or
                    ".ts" in url or ".mp4" in url)
                    
        return is_xhr or is_media

    def _analyze_traffic_type(self, url: str, initiator: str = "") -> str:
        """
        URL ve Çağıran (Initiator) bilgisine bakarak trafiğin amacını belirler.
        Dönüş Değeri: 'api', 'tracker', 'script' veya 'ignore'
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

    def capture_network_logs(self) -> list[dict]:
        """
        Sitenin dış dünya ile iletişimini (API, XHR, Tracker) analiz eder.
        Görsel, CSS ve Medya dosyalarını filtreler.
        """
        relevant_logs = []
        
        # --- YÖNTEM 1: Driver Logları (Plan A) ---
        try:
            logs = self.driver.get_log("performance")
            for entry in logs:
                try:
                    log_json = json.loads(entry["message"])
                    message = log_json["message"]
                    
                    if message["method"] == "Network.responseReceived":
                        params = message["params"]
                        resp = params.get("response", {})
                        url = resp.get("url", "")
                        
                        # Initiator bilgisini driver loglarından çıkarmak zor olur,
                        # bu yüzden MIME type ve URL analizine güveniyoruz.
                        traffic_type = self._analyze_traffic_type(url, params.get("type", "").lower())
                        
                        if traffic_type != "ignore":
                            relevant_logs.append({
                                "source": "driver",
                                "type": traffic_type,  # api, script, tracker
                                "domain": url.split('/')[2],  # Sadece domain (örn: api.google.com)
                                "url": url,
                                "status": resp.get("status", 0),
                                "size": resp.get("encodedDataLength", 0)
                            })
                except: continue

            # Logları okuduktan sonra temizle (Hata #2 düzeltmesi)
            try:
                self.driver.get_log("performance")
            except Exception:
                pass
            
            if relevant_logs:
                logger.info(f"✅ Driver Loglarından {len(relevant_logs)} iletişim kaydı alındı.")
                return relevant_logs

        except Exception:
            logger.warning("⚠️ Driver loglarına erişilemedi. JS Fallback (Plan B) devreye giriyor...")

        # --- YÖNTEM 2: JS Performance API (Plan B - Fallback) ---
        # BURASI ÇOK ÖNEMLİ: initiatorType alıyoruz!
        try:
            js_script = """
            return performance.getEntriesByType("resource").map(r => ({
                url: r.name,
                initiatorType: r.initiatorType,  // xmlhttprequest, fetch, script, img, link...
                size: r.transferSize || 0,
                time: r.startTime
            }));
            """
            js_logs = self.driver.execute_script(js_script)
            
            for log in js_logs:
                url = log.get("url", "")
                initiator = log.get("initiatorType", "").lower()
                
                # Yeni analiz fonksiyonunu kullan
                traffic_type = self._analyze_traffic_type(url, initiator)
                
                if traffic_type != "ignore":
                    domain = url.split('/')[2] if '//' in url else url
                    
                    relevant_logs.append({
                        "source": "js_fallback",
                        "type": traffic_type,  # api, script, tracker
                        "domain": domain,     # İletişim kurulan sunucu
                        "initiator": initiator,  # İstek türü (fetch, xhr)
                        "url": url,
                        "status": 200,
                        "size": log.get("size", 0)
                    })
            
            if relevant_logs:
                logger.info(f"✅ JS Fallback ile {len(relevant_logs)} iletişim kaydı analiz edildi.")

        except Exception as e:
            logger.error(f"❌ Trafik analizi yapılamadı: {e}")

        return relevant_logs

    def process(self, req: ScrapeRequest) -> ScrapeResponse:
        """
        İstemi işler ve yanıt döndürür

        Args:
            req: ScrapeRequest nesnesi

        Returns:
            ScrapeResponse nesnesi
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
                domain = raw_url.replace("https://", "").replace("http://", "").split("/")[0]
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
                try:
                    self.driver.get_log("performance")
                except Exception:
                    pass
                
                # ADIM 1: HAM URL
                if req.process_raw_url:
                    log(f"Adım 1: Ham URL -> {raw_url}")
                    try:
                        self.driver.get(raw_url)
                    except Exception as e:
                        log(f"Sayfa yüklenemedi: {str(e)}")
                        raise
                    self.solve_captcha_and_consent(logs)
                    self.smart_wait_and_kill(req.wait_time, logs)
                    
                    # Body check geliştirildi - JavaScript yüklenmesi için bekleme eklendi (Hata #8 düzeltmesi)
                    time.sleep(2)  # JavaScript yüklenmesi için bekleme
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(body_text) < 100:
                        logger.warning("Sayfa içeriği çok az, sayfa yeniden yükleniyor...")
                        self.driver.refresh()
                        time.sleep(5)  # Yükleme süresi artırıldı

                    res.raw_desktop_ss = self.get_b64_screenshot()
                    if req.get_html:
                        res.raw_html = self.get_b64_html()
                    
                    # MOBİL - Opsiyonel
                    if req.get_mobile_ss:
                        log("📱 Mobil Modu...")
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

                # ADIM 2: ANA DOMAIN
                if req.process_main_domain:
                    if raw_url.rstrip('/') == main_domain_url.rstrip('/'):
                        if res.raw_desktop_ss:
                            res.main_desktop_ss = res.raw_desktop_ss
                        else:
                            log(f"Adım 2: Ana Domain -> {main_domain_url}")
                            self.driver.get(main_domain_url)
                            self.solve_captcha_and_consent(logs)
                            self.smart_wait_and_kill(req.wait_time, logs)
                            res.main_desktop_ss = self.get_b64_screenshot()
                    else:
                        log(f"Adım 2: Ana Domain -> {main_domain_url}")
                        self.driver.get(main_domain_url)
                        self.solve_captcha_and_consent(logs)
                        self.smart_wait_and_kill(req.wait_time, logs)
                        res.main_desktop_ss = self.get_b64_screenshot()
 
                # 🔥 KRİTİK HAMLE: Google'a gitmeden önce AĞ TRAFİĞİNİ YAKALA! 🔥
                if req.capture_network_logs:
                    log("📡 Hedef site trafiği yedekleniyor...")
                    network_data = self.capture_network_logs()
                    log(f"✅ {len(network_data)} adet kritik ağ isteği yakalandı.")
                
                # -------------------------------------------------------
                # BURADAN SONRA TARAYICI BAŞKA SİTELERE GİDECEK
                # -------------------------------------------------------

                # ADIM 3: GOOGLE ARAMASI (Opsiyonel)
                if req.get_google_search:
                    log(f"🔍 Google: {domain}")
                    self.driver.get(f"https://www.google.com/search?q=site:{domain}")
                    time.sleep(3)
                    self.solve_captcha_and_consent(logs, is_google=True)
                    res.google_ss = self.get_b64_screenshot()
                    if req.get_google_html:
                        res.google_html = self.get_b64_html()

                # ADIM 4: DUCKDUCKGO ARAMASI (Opsiyonel)
                if req.get_ddg_search:
                    log(f"🦆 DDG: {domain}")
                    self.driver.get(f"https://duckduckgo.com/?q=site:{domain}")
                    time.sleep(3)
                    res.ddg_ss = self.get_b64_screenshot()
                    if req.get_ddg_html:
                        res.ddg_html = self.get_b64_html()
                
                # Ağ trafiği verisini yanıta ekle
                if req.capture_network_logs:
                    res.network_logs = network_data

                res.status = "success"
                log("✅ Bitti")

            except Exception as e:
                log(f"❌ HATA: {str(e)}")
                res.status = "error"
                self.restart()

            res.logs = logs
            res.duration = time.time() - start_time
            return res

        finally:
            self.lock.release()
