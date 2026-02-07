"""
Scrape Processor Sınıfı
Ana scrape işleme mantığı
"""
import time
from typing import Any
from urllib.parse import urlparse, quote
from selenium.webdriver.common.by import By

from app.config import settings
from app.schemas import ScrapeRequest, ScrapeResponse
from app.core.logger import loguru_logger as logger
from app.core.blacklist import blacklist_manager
from app.core.browser.popup_handler import PopupHandler
from app.core.browser.screenshot_helper import ScreenshotHelper
from app.core.browser.network_logger import NetworkLogger


class ScrapeProcessor:
    """
    Scrape processor sınıfı
    Ana scrape işleme mantığını yönetir
    """
    
    def __init__(self, driver: Any, popup_handler: PopupHandler, 
                 screenshot_helper: ScreenshotHelper, network_logger: NetworkLogger):
        """
        Scrape processor başlat
        
        Args:
            driver: SeleniumBase driver instance
            popup_handler: Popup handler instance
            screenshot_helper: Screenshot helper instance
            network_logger: Network logger instance
        """
        self.driver = driver
        self.popup_handler = popup_handler
        self.screenshot_helper = screenshot_helper
        self.network_logger = network_logger
    
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
        start_time = time.time()
        logs = []
        network_data = []  # Ağ trafiği verisi en başta tanımla
        res = ScrapeResponse(status="processing", logs=[], duration=0)
        
        def log(m: str):
            logs.append(m)
            logger.info(f"[{req.url}] {m}")

        try:
            raw_url = req.url
            if not raw_url.startswith("http"):
                raw_url = "https://" + raw_url
            parsed = urlparse(raw_url)
            domain = parsed.netloc
            if ':' in domain:
                domain = domain.split(':')[0]
            main_domain_url = f"https://{domain}"

            # ADIM 1: HAM URL
            if req.process_raw_url:
                log(f"Adım 1: Ham URL -> {raw_url}")
                try:
                    self.driver.get(raw_url)
                except Exception as e:
                    log("Sayfa yüklenemedi")
                    raise
                self.popup_handler.solve_captcha_and_consent(logs)
                self.popup_handler.smart_wait_and_kill(req.wait_time, logs)
                
                # Body check - JavaScript yüklenmesi için bekleme
                time.sleep(settings.body_check_wait_time if hasattr(settings, 'body_check_wait_time') else 2)
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if len(body_text) < 100:
                    logger.warning("Sayfa içeriği çok az, sayfa yeniden yükleniyor...")
                    self.driver.refresh()
                    time.sleep(settings.page_reload_wait_time if hasattr(settings, 'page_reload_wait_time') else 5)

                res.raw_desktop_ss = self.screenshot_helper.get_b64_screenshot()
                if req.get_html:
                    res.raw_html = self.screenshot_helper.get_b64_html()
                
                # MOBİL - Opsiyonel
                if req.get_mobile_ss:
                    log(f"Adım 2: 📱 Mobil -> {raw_url}")
                    try:
                        self.driver.execute_cdp_cmd(
                            "Emulation.setDeviceMetricsOverride",
                            {"width": 375, "height": 812, "deviceScaleFactor": 3, "mobile": True}
                        )
                        self.driver.refresh()
                        
                        time.sleep(settings.mobile_wait_time)
                        self.popup_handler.solve_captcha_and_consent(logs)
                        self.popup_handler.smart_wait_and_kill(req.wait_time, logs, mobile_mode=True)
                        
                        res.raw_mobile_ss = self.screenshot_helper.get_b64_screenshot()
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
                        self.popup_handler.solve_captcha_and_consent(logs)
                        self.popup_handler.smart_wait_and_kill(req.wait_time, logs)
                        res.main_desktop_ss = self.screenshot_helper.get_b64_screenshot()
                else:
                    log(f"Adım 3: Ana Domain -> {main_domain_url}")
                    self.driver.get(main_domain_url)
                    self.popup_handler.solve_captcha_and_consent(logs)
                    self.popup_handler.smart_wait_and_kill(req.wait_time, logs)
                    res.main_desktop_ss = self.screenshot_helper.get_b64_screenshot()

            # 🔥 KRİTİK HAMLE: Google'a gitmeden önce AĞ TRAFİĞİNİ YAKALA! 🔥
            if req.capture_network_logs:
                log("📡 Hedef site trafiği toplanıyor...")
                network_data = self.network_logger.capture_network_logs()
                log(f"✅ {len(network_data)} adet kritik ağ isteği yakalandı.")
            
            # -------------------------------------------------------
            # BURADAN SONRA TARAYICI BAŞKA SİTELERE GİDECEK
            # -------------------------------------------------------

            # ADIM 3: GOOGLE ARAMASI (Opsiyonel)
            if req.get_google_search:
                log(f"Adım 4: 🔍 Google -> {domain}")
                safe_domain = quote(domain, safe='')
                self.driver.get(f"https://www.google.com/search?q=site%3A{safe_domain}")
                time.sleep(settings.search_engine_wait_time)
                self.popup_handler.solve_captcha_and_consent(logs, is_google=True)
                res.google_ss = self.screenshot_helper.get_b64_screenshot()
                if req.get_google_html:
                    res.google_html = self.screenshot_helper.get_b64_html()

            # ADIM 4: DUCKDUCKGO ARAMASI (Opsiyonel)
            if req.get_ddg_search:
                log(f"Adım 5: 🦆 DDG -> {domain}")
                safe_domain = quote(domain, safe='')
                self.driver.get(f"https://duckduckgo.com/?q=site%3A{safe_domain}")
                time.sleep(settings.search_engine_wait_time)
                res.ddg_ss = self.screenshot_helper.get_b64_screenshot()
                if req.get_ddg_html:
                    res.ddg_html = self.screenshot_helper.get_b64_html()
            
            # Ağ trafiği verisini yanıta ekle
            if req.capture_network_logs:
                res.network_logs = network_data

            res.status = "success"
            log(f"✅ Bitti -> {domain}")

        except Exception as e:
            log(f"❌ HATA: {str(e)}")
            res.status = "error"
            logger.error(f"Scrape işlemi başarısız: {req.url} - {str(e)}", exc_info=True)
            
            # Hata yukarı fırlat - BrowserManager'da restart yapılacak
            raise

        res.logs = logs
        res.duration = time.time() - start_time

        return res
