"""
Memory Monitor Modülü
RAM kullanımını periyodik olarak kontrol eder ve aşırı kullanımda uyarı verir.

Bu modül:
1. RAM kullanımını periyodik kontrol eder
2. Belirli bir eşiğin üzerindeyse alert verir
3. Otomatik cleanup tetikler
"""
import threading
import time
import gc
from typing import Optional, Callable
from loguru import logger


class MemoryMonitor:
    """
    Memory Monitoring Sınıfı
    
    RAM kullanımını izler ve belirli bir eşiğin üzerindeyse
    uyarı verir ve cleanup fonksiyonlarını tetikler.
    """
    
    def __init__(
        self,
        check_interval: int = 300,
        memory_threshold_mb: int = 1024,
        critical_threshold_mb: int = 2048
    ):
        """
        Memory Monitor başlat
        
        Args:
            check_interval: Kontrol aralığı (saniye), varsayılan 5 dakika
            memory_threshold_mb: Uyarı eşiği (MB), varsayılan 1 GB
            critical_threshold_mb: Kritik eşiği (MB), varsayılan 2 GB
        """
        self._check_interval = check_interval
        self._memory_threshold_mb = memory_threshold_mb
        self._critical_threshold_mb = critical_threshold_mb
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cleanup_callbacks: list[Callable] = []
        self._lock = threading.Lock()
    
    def add_cleanup_callback(self, callback: Callable) -> None:
        """
        Cleanup callback fonksiyonu ekle
        
        Args:
            callback: Memory aşımı durumunda çağrılacak fonksiyon
        """
        with self._lock:
            self._cleanup_callbacks.append(callback)
            logger.debug(f"Memory cleanup callback eklendi: {callback.__name__}")
    
    def start(self) -> None:
        """Memory monitoring'i başlat"""
        with self._lock:
            if self._running:
                logger.warning("⚠️ Memory Monitor zaten çalışıyor")
                return
            
            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="MemoryMonitor"
            )
            self._thread.start()
            logger.info(
                f"✅ Memory Monitor başlatıldı (Kontrol aralığı: {self._check_interval}s, "
                f"Uyarı eşiği: {self._memory_threshold_mb} MB, "
                f"Kritik eşiği: {self._critical_threshold_mb} MB)"
            )
    
    def stop(self) -> None:
        """Memory monitoring'i durdur"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            # Thread'in bitmesini bekle
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            
            logger.info("🔌 Memory Monitor durduruldu")
    
    def _monitor_loop(self) -> None:
        """Monitoring döngüsü"""
        try:
            while self._running:
                try:
                    self._check_memory()
                except Exception as e:
                    logger.error(f"Memory monitoring hatası: {e}")
                
                time.sleep(self._check_interval)
        except Exception as e:
            logger.error(f"Memory monitor döngüsü hatası: {e}")
    
    def _check_memory(self) -> None:
        """Memory kullanımını kontrol et"""
        try:
            import psutil
            
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # RSS (Resident Set Size) - fiziksel RAM kullanımı
            memory_mb = memory_info.rss / 1024 / 1024
            
            # VMS (Virtual Memory Size) - sanal bellek kullanımı
            vms_mb = memory_info.vms / 1024 / 1024
            
            # Memory yüzdesi
            memory_percent = process.memory_percent()
            
            logger.debug(
                f"Memory: {memory_mb:.2f} MB (VMS: {vms_mb:.2f} MB, "
                f"Yüzde: {memory_percent:.2f}%)"
            )
            
            # Kritik eşik kontrolü
            if memory_mb > self._critical_threshold_mb:
                logger.error(
                    f"🚨 KRİTİK Yüksek RAM kullanımı: {memory_mb:.2f} MB "
                    f"(Kritik Eşik: {self._critical_threshold_mb} MB)"
                )
                self._trigger_cleanup(force=True)
            
            # Uyarı eşik kontrolü
            elif memory_mb > self._memory_threshold_mb:
                logger.warning(
                    f"⚠️ Yüksek RAM kullanımı: {memory_mb:.2f} MB "
                    f"(Uyarı Eşiği: {self._memory_threshold_mb} MB)"
                )
                self._trigger_cleanup(force=False)
        
        except ImportError:
            logger.warning("psutil paketi bulunamadı, memory monitoring devre dışı")
            self.stop()
        except Exception as e:
            logger.error(f"Memory kontrol hatası: {e}")
    
    def _trigger_cleanup(self, force: bool = False) -> None:
        """
        Cleanup callback'lerini tetikle
        
        Args:
            force: Zorla cleanup yap
        """
        logger.info("🧹 Memory cleanup tetikleniyor...")
        
        # Python garbage collection'ı tetikle
        if force:
            collected = gc.collect()
            logger.info(f"🗑️ Python GC: {collected} nesne temizlendi")
        
        # Callback fonksiyonlarını çağır
        with self._lock:
            for callback in self._cleanup_callbacks:
                try:
                    logger.debug(f"Cleanup callback çağrılıyor: {callback.__name__}")
                    callback()
                except Exception as e:
                    logger.error(f"Cleanup callback hatası ({callback.__name__}): {e}")
    
    def get_memory_info(self) -> dict:
        """
        Güncel memory bilgilerini al
        
        Returns:
            dict: Memory bilgileri
        """
        try:
            import psutil
            
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "threshold_mb": self._memory_threshold_mb,
                "critical_threshold_mb": self._critical_threshold_mb,
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
_memory_monitor: Optional[MemoryMonitor] = None
_monitor_lock = threading.Lock()


def get_memory_monitor() -> MemoryMonitor:
    """
    Memory Monitor singleton instance'ını al
    
    Returns:
        MemoryMonitor: Singleton instance
    """
    global _memory_monitor
    
    with _monitor_lock:
        if _memory_monitor is None:
            _memory_monitor = MemoryMonitor()
        
        return _memory_monitor
