"""
Network Logger Sınıfı
Network log yakalama işlemleri
"""
import json
from typing import Any, List

from app.core.logger import loguru_logger as logger


class NetworkLogger:
    """
    Network logger sınıfı
    Network log yakalama işlemlerini yönetir
    """
    
    def __init__(self, driver: Any):
        """
        Network logger başlat
        
        Args:
            driver: SeleniumBase driver instance
        """
        self.driver = driver
    
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
        except Exception:
            # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
            # Bu durumda JS Performance API fallback kullanılır
            pass  # JS fallback kullanılıyor, log gereksiz
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
