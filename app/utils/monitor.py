"""
System Monitor Modülü
Sistem kaynaklarını izler ve otomatik temizlik mekanizması sağlar.

Bu modül:
1. Ana uygulama process'inin RAM/CPU kullanımını izler
2. Çocuk Chrome süreçlerini izler
3. /tmp disk kullanımını kontrol eder ve 1GB üzerine çıkarsa cleanup tetikler
4. Memory profiling için destek sağlar
"""
import threading
import time
import platform
import shutil
from typing import Optional, Callable, Dict, Any, List
from loguru import logger


class SystemMonitor:
    """
    System Monitoring Sınıfı
    
    Sistem kaynaklarını izler ve belirli eşiğin üzerindeyse
    uyarı verir ve cleanup fonksiyonlarını tetikler.
    """
    
    def __init__(
        self,
        check_interval: int = 60,
        tmp_threshold_mb: int = 1024
    ):
        """
        System Monitor başlat
        
        Args:
            check_interval: Kontrol aralığı (saniye), varsayılan 60
            tmp_threshold_mb: /tmp eşiği (MB), varsayılan 1024 (1GB)
        """
        self._check_interval = check_interval
        self._tmp_threshold_mb = tmp_threshold_mb
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cleanup_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        # /tmp yolu (platform bağımsız)
        self._tmp_path = self._get_tmp_path()
    
    def _get_tmp_path(self) -> str:
        """
        Platform bağımsız /tmp yolunu al
        
        Returns:
            /tmp yolu
        """
        if platform.system() == "Windows":
            # Windows için TEMP ortam değişkenini kullan
            import os
            return os.environ.get('TEMP', 'C:\\Temp')
        return '/tmp'
    
    def add_cleanup_callback(self, callback: Callable) -> None:
        """
        Cleanup callback fonksiyonu ekle
        
        Args:
            callback: /tmp aşımı durumunda çağrılacak fonksiyon
        """
        with self._lock:
            self._cleanup_callbacks.append(callback)
            logger.debug(f"System cleanup callback eklendi: {callback.__name__}")
    
    def start(self) -> None:
        """System monitoring'i başlat"""
        with self._lock:
            if self._running:
                logger.warning("⚠️ System Monitor zaten çalışıyor")
                return
            
            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="SystemMonitor"
            )
            self._thread.start()
            logger.info(
                f"✅ System Monitor başlatıldı (Kontrol aralığı: {self._check_interval}s, "
                f"/tmp eşiği: {self._tmp_threshold_mb} MB, "
                f"Yol: {self._tmp_path})"
            )
    
    def stop(self) -> None:
        """System monitoring'i durdur"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            # Thread'in bitmesini bekle
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            
            logger.info("🔌 System Monitor durduruldu")
    
    def _monitor_loop(self) -> None:
        """Monitoring döngüsü"""
        try:
            while self._running:
                try:
                    self._check_main_process()
                    self._check_chrome_processes()
                    self._check_tmp_disk_usage()
                except Exception as e:
                    logger.error(f"System monitoring hatası: {e}")
                
                time.sleep(self._check_interval)
        except Exception as e:
            logger.error(f"System monitor döngüsü hatası: {e}")
    
    def _check_main_process(self) -> None:
        """Ana uygulamanın RAM/CPU kullanımını kontrol et"""
        try:
            import psutil
            
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # RSS (Resident Set Size) - fiziksel RAM kullanımı
            rss_mb = memory_info.rss / 1024 / 1024
            
            # VMS (Virtual Memory Size) - sanal bellek kullanımı
            vms_mb = memory_info.vms / 1024 / 1024
            
            # Memory yüzdesi
            memory_percent = process.memory_percent()
            
            # CPU kullanımı
            cpu_percent = process.cpu_percent()
            
            logger.debug(
                f"Main Process - RAM: {rss_mb:.2f} MB (VMS: {vms_mb:.2f} MB, "
                f"Yüzde: {memory_percent:.2f}%), CPU: {cpu_percent:.2f}%"
            )
        
        except ImportError:
            logger.warning("psutil paketi bulunamadı, main process monitoring devre dışı")
        except Exception as e:
            logger.error(f"Main process kontrol hatası: {e}")
    
    def _check_chrome_processes(self) -> None:
        """Çocuk Chrome süreçlerini bul ve izle"""
        try:
            import psutil
            
            chrome_processes = []
            total_ram_mb = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    if 'chrome' in proc_name or 'chromedriver' in proc_name:
                        rss_mb = proc.info['memory_info'].rss / 1024 / 1024
                        cpu = proc.info['cpu_percent']
                        total_ram_mb += rss_mb
                        
                        chrome_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'ram_mb': rss_mb,
                            'cpu_percent': cpu
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if chrome_processes:
                logger.debug(
                    f"Chrome Processes: {len(chrome_processes)} found, "
                    f"Toplam RAM: {total_ram_mb:.2f} MB"
                )
        
        except ImportError:
            logger.warning("psutil paketi bulunamadı, chrome process monitoring devre dışı")
        except Exception as e:
            logger.error(f"Chrome process kontrol hatası: {e}")
    
    def _check_tmp_disk_usage(self) -> None:
        """/tmp disk kullanımını kontrol et"""
        try:
            import os
            
            # /tmp dizininin gerçek kullanımını hesapla (disk partition değil)
            used_bytes = 0
            for root, dirs, files in os.walk(self._tmp_path):
                for name in files:
                    try:
                        filepath = os.path.join(root, name)
                        # Sembolik linkleri takip etme
                        if not os.path.islink(filepath):
                            used_bytes += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        continue
            
            used_mb = used_bytes / 1024 / 1024
            
            logger.debug(
                f"{self._tmp_path} Kullanımı: {used_mb:.2f} MB"
            )
            
            # Eşik kontrolü
            if used_mb > self._tmp_threshold_mb:
                logger.warning(
                    f"⚠️ {self._tmp_path} kullanımı yüksek: {used_mb:.2f} MB "
                    f"(Eşik: {self._tmp_threshold_mb} MB)"
                )
                self._trigger_cleanup(force=True)
        
        except Exception as e:
            logger.error(f"Tmp disk kontrol hatası: {e}")
    
    def _trigger_cleanup(self, force: bool = False) -> None:
        """
        Cleanup callback'lerini tetikle
        
        Args:
            force: Zorla cleanup yap
        """
        logger.info("🧹 System cleanup tetikleniyor...")
        
        # Callback fonksiyonlarını çağır
        with self._lock:
            for callback in self._cleanup_callbacks:
                try:
                    logger.debug(f"Cleanup callback çağrılıyor: {callback.__name__}")
                    callback()
                except Exception as e:
                    logger.error(f"Cleanup callback hatası ({callback.__name__}): {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Güncel sistem bilgilerini al
        
        Returns:
            dict: Sistem bilgileri
        """
        try:
            import psutil
            
            # Ana process bilgileri
            process = psutil.Process()
            memory_info = process.memory_info()
            
            main_process_info = {
                "pid": process.pid,
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent()
            }
            
            # Chrome process bilgileri
            chrome_processes = []
            total_chrome_ram_mb = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    if 'chrome' in proc_name or 'chromedriver' in proc_name:
                        rss_mb = proc.info['memory_info'].rss / 1024 / 1024
                        total_chrome_ram_mb += rss_mb
                        
                        chrome_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'ram_mb': rss_mb,
                            'cpu_percent': proc.info['cpu_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # /tmp disk bilgileri (gerçek kullanım)
            import os
            used_bytes = 0
            for root, dirs, files in os.walk(self._tmp_path):
                for name in files:
                    try:
                        filepath = os.path.join(root, name)
                        if not os.path.islink(filepath):
                            used_bytes += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        continue
            
            tmp_info = {
                "path": self._tmp_path,
                "used_mb": used_bytes / 1024 / 1024,
                "threshold_mb": self._tmp_threshold_mb
            }
            
            return {
                "main_process": main_process_info,
                "chrome_processes": {
                    "count": len(chrome_processes),
                    "total_ram_mb": total_chrome_ram_mb,
                    "processes": chrome_processes
                },
                "tmp_usage": tmp_info,
                "check_interval": self._check_interval,
                "running": self._running
            }
        
        except ImportError:
            return {
                "error": "psutil paketi bulunamadı"
            }
        except Exception as e:
            return {
                "error": str(e)
            }


# Singleton instance
_system_monitor: Optional[SystemMonitor] = None
_monitor_lock = threading.Lock()


def get_system_monitor() -> SystemMonitor:
    """
    System Monitor singleton instance'ını al
    
    Returns:
        SystemMonitor: Singleton instance
    """
    global _system_monitor
    
    with _monitor_lock:
        if _system_monitor is None:
            _system_monitor = SystemMonitor()
        
        return _system_monitor
