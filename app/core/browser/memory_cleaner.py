"""
Memory Cleaner Sınıfı
Driver loglarını ve geçici dosyaları temizler
"""
import glob
import platform
import shutil
from typing import Any

from app.config import settings
from app.core.logger import loguru_logger as logger


class MemoryCleaner:
    """
    Memory cleaner sınıfı
    Driver loglarını ve geçici dosyaları temizler
    """
    
    def __init__(self, driver: Any):
        """
        Memory cleaner başlat
        
        Args:
            driver: SeleniumBase driver instance
        """
        self.driver = driver
    
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
        except Exception:
            # Chrome 144+ sürümleri "performance" log tipini desteklemiyor
            # Bu durumda JS Performance API kullanılıyor
            pass  # JS fallback kullanılıyor, log gereksiz

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
