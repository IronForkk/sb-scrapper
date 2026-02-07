"""
Captcha Solver Sınıfı
Captcha çözme işlemleri
"""
from typing import Any, List


class CaptchaSolver:
    """
    Captcha solver sınıfı
    Captcha çözme işlemlerini yönetir
    """
    
    def __init__(self, popup_handler: Any):
        """
        Captcha solver başlat
        
        Args:
            popup_handler: Popup handler instance
        """
        self.popup_handler = popup_handler
    
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
        # Popup handler'dan solve_captcha_and_consent metodunu çağır
        self.popup_handler.solve_captcha_and_consent(logs, is_google)
