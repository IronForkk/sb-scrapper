"""
Popup Handler Sınıfı
Smart wait ve popup temizleme işlemleri
"""
import time
import random
from typing import Any, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from app.config import settings
from app.core.logger import loguru_logger as logger
from app.payloads.sentinel_js import JS_SENTINEL


class PopupHandler:
    """
    Popup handler sınıfı
    Smart wait ve popup temizleme işlemlerini yönetir
    """
    
    def __init__(self, driver: Any):
        """
        Popup handler başlat
        
        Args:
            driver: SeleniumBase driver instance
        """
        self.driver = driver
    
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
                time.sleep(settings.frame_switch_wait_time)
                for selector in selectors:
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if checkbox.is_displayed():
                            self.human_click(checkbox)
                            logs.append(log_msg)
                            time.sleep(settings.consent_click_wait_time)
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
                            time.sleep(settings.consent_click_wait_time)
                            break
                    except Exception:
                        pass

            # Cloudflare
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='cloudflare']")
            if frames:
                logs.append("🛡️ Cloudflare tespit edildi...")
                self.driver.switch_to.frame(frames[0])
                time.sleep(settings.frame_switch_wait_time)
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
                time.sleep(settings.consent_click_wait_time)
                self.driver.switch_to.default_content()
            
            # ReCaptcha
            frames_re = self.driver.find_elements(By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")
            if frames_re:
                self.driver.switch_to.frame(frames_re[0])
                try:
                    box = self.driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-border")
                    self.human_click(box)
                    logs.append("✅ ReCaptcha Tıklandı")
                    time.sleep(settings.consent_click_wait_time)
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
                time.sleep(settings.consent_click_wait_time)
            
            # HCaptcha (YENİ)
            hcaptcha_selectors = [
                ".h-captcha-checkbox",
                ".hcaptcha-checkbox",
                "input[type='checkbox']",
                "[aria-label='hCaptcha']"
            ]
            if self._switch_and_click_in_frame("iframe[src*='hcaptcha']", hcaptcha_selectors, logs, "✅ HCaptcha Checkbox Tıklandı"):
                time.sleep(settings.consent_click_wait_time)
                
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
