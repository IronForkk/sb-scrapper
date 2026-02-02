"""
Async Task Queue (Singleton Pattern)
Arka planda çalışan görevler için asenkron kuyruk

Bu kuyruk, Redis kullanmadan çalışır ve singleton pattern kullanır.
Görevler bellekte tutulur ve worker thread'ler tarafından işlenir.
"""
import threading
import queue
import asyncio
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
from loguru import logger


# Thread-local event loop storage
_thread_local = threading.local()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Thread-local event loop al veya oluştur
    
    Returns:
        asyncio.AbstractEventLoop: Thread-local event loop
    """
    if not hasattr(_thread_local, 'loop'):
        _thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_thread_local.loop)
    return _thread_local.loop


def _cleanup_event_loop() -> None:
    """Thread-local event loop'u temizle
    
    Returns:
        None
    """
    if hasattr(_thread_local, 'loop') and _thread_local.loop:
        try:
            # Önce tüm pending task'ları iptal et
            pending = asyncio.all_tasks(_thread_local.loop)
            for task in pending:
                task.cancel()
            
            # Task'ların bitmesini bekle
            if pending:
                try:
                    _thread_local.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                except Exception:
                    pass
            
            _thread_local.loop.close()
        except Exception:
            pass
        finally:
            # Thread-local event loop'u temizle
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass
            delattr(_thread_local, 'loop')


class TaskStatus(str, Enum):
    """Görev durumları"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Görev veri yapısı"""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Görev bilgilerini sözlüğe çevir"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "result": self.result if self.status == TaskStatus.COMPLETED else None,
            "error": self.error if self.status == TaskStatus.FAILED else None,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class AsyncTaskQueue:
    """
    Asenkron Görev Kuyruğu (Singleton)
    
    Bu sınıf, Redis kullanmadan arka planda çalışan görevler için
    asenkron kuyruk sağlar. Thread-safe singleton pattern kullanır.
    """
    _instance: Optional['AsyncTaskQueue'] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    
    def __new__(cls) -> 'AsyncTaskQueue':
        """Singleton pattern - tek bir instance oluştur"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """AsyncTaskQueue başlat"""
        # Singleton kontrolü
        with AsyncTaskQueue._lock:
            if AsyncTaskQueue._initialized:
                return
            
            self._task_queue: queue.Queue = queue.Queue()
            self._tasks: Dict[str, Task] = {}
            self._workers: list[threading.Thread] = []
            self._running: bool = False
            self._worker_count: int = 2  # Varsayılan worker sayısı
            self._task_counter: int = 0
            self._task_lock: threading.Lock = threading.Lock()
            
            # Otomatik temizleme ayarları
            self._max_task_history = 1000  # Maksimum task history
            self._cleanup_interval = 3600  # 1 saatte bir temizle
            self._last_cleanup_time = time.time()
            
            AsyncTaskQueue._initialized = True
            logger.info("✅ AsyncTaskQueue singleton başlatıldı")
    
    def start(self, worker_count: int = 2) -> None:
        """
        Worker thread'leri başlat
        
        Args:
            worker_count: Worker thread sayısı
        """
        with self._task_lock:
            if self._running:
                logger.warning("⚠️ AsyncTaskQueue zaten çalışıyor")
                return
            
            self._worker_count = worker_count
            self._running = True
            
            # Worker thread'leri oluştur ve başlat
            for i in range(worker_count):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskWorker-{i}",
                    daemon=True
                )
                worker.start()
                self._workers.append(worker)
            
            logger.info(f"✅ AsyncTaskQueue başlatıldı ({worker_count} worker)")
    
    def stop(self) -> None:
        """
        Worker thread'leri durdur
        Event leak önlemek için tüm worker thread'lerinin event loop'ları temizlenir
        """
        with self._task_lock:
            if not self._running:
                return
            
            self._running = False
            
            # Kuyruğa stop sinyali gönder
            for _ in range(self._worker_count):
                self._task_queue.put(None)
            
            # Worker thread'lerinin bitmesini bekle
            for worker in self._workers:
                worker.join(timeout=10)
            
            self._workers.clear()
            
            # Tüm thread-local event loop'ları temizle
            # Her worker kendi event loop'unu temizlemeli ama garanti için ek kontrol
            try:
                # Ana thread'de kalan event loop'u temizle
                loop = asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    # Tüm pending task'ları iptal et
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    # Task'ların bitmesini bekle
                    if pending:
                        try:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                    
                    loop.close()
                
                # Thread-local event loop'u temizle
                asyncio.set_event_loop(None)
            except Exception:
                pass
            
            logger.info("🔌 AsyncTaskQueue durduruldu")
    
    def _worker_loop(self) -> None:
        """Worker thread döngüsü"""
        logger.debug(f"Worker thread başladı: {threading.current_thread().name}")
        
        try:
            while self._running:
                try:
                    # Kuyruktan görev al (timeout ile)
                    task = self._task_queue.get(timeout=1.0)
                    
                    # Stop sinyali
                    if task is None:
                        break
                    
                    # Görevi çalıştır
                    self._execute_task(task)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"❌ Worker thread hatası: {e}", exc_info=True)
        finally:
            # Thread kapanırken event loop'u temizle
            _cleanup_event_loop()
            logger.debug(f"Worker thread durduruldu: {threading.current_thread().name}")
    
    def _execute_task(self, task: Task) -> None:
        """
        Görevi çalıştır
        
        Args:
            task: Çalıştırılacak görev
        """
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        logger.info(f"🔄 Görev başlatıldı: {task.name} (ID: {task.id})")
        
        try:
            # Görevi çalıştır (async veya sync)
            if asyncio.iscoroutinefunction(task.func):
                # Thread-local event loop'u kullan
                loop = _get_event_loop()
                result = loop.run_until_complete(task.func(*task.args, **task.kwargs))
            else:
                # Sync fonksiyon
                result = task.func(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            duration = task.completed_at - task.started_at
            logger.info(f"✅ Görev tamamlandı: {task.name} (ID: {task.id}, Süre: {duration:.2f}s)")
        
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            
            # Retry kontrolü
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                self._task_queue.put(task)
                logger.warning(
                    f"⚠️ Görev yeniden kuyruğa alındı: {task.name} "
                    f"(ID: {task.id}, Retry: {task.retry_count}/{task.max_retries})"
                )
            else:
                logger.error(
                    f"❌ Görev başarısız: {task.name} (ID: {task.id}, Hata: {e})",
                    exc_info=True
                )
    
    def submit(
        self,
        func: Callable,
        name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> str:
        """
        Yeni görev ekle
        
        Args:
            func: Çalıştırılacak fonksiyon
            name: Görev adı
            args: Fonksiyon argümanları
            kwargs: Fonksiyon keyword argümanları
            max_retries: Maksimum retry sayısı
        
        Returns:
            str: Görev ID'si
        """
        if kwargs is None:
            kwargs = {}
        
        with self._task_lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
            
            # Otomatik temizleme kontrolü
            self._auto_cleanup()
        
        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries
        )
        
        self._tasks[task_id] = task
        self._task_queue.put(task)
        
        logger.info(f"📝 Görev eklendi: {name} (ID: {task_id})")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Görev bilgilerini al
        
        Args:
            task_id: Görev ID'si
        
        Returns:
            Dict[str, Any]: Görev bilgileri veya None
        """
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Tüm görevleri al
        
        Returns:
            Dict[str, Dict[str, Any]]: Tüm görevler
        """
        return {
            task_id: task.to_dict()
            for task_id, task in self._tasks.items()
        }
    
    def _auto_cleanup(self):
        """Otomatik task temizleme"""
        current_time = time.time()
        
        # Belirli aralıklarla temizle
        if current_time - self._last_cleanup_time < self._cleanup_interval:
            return
        
        completed_count = sum(
            1 for task in self._tasks.values()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        )
        
        if completed_count > self._max_task_history:
            # En eski tamamlanan görevleri sil
            sorted_tasks = sorted(
                self._tasks.items(),
                key=lambda x: x[1].completed_at or 0
            )
            to_remove = completed_count - self._max_task_history
            
            removed_count = 0
            for i in range(to_remove):
                task_id, task = sorted_tasks[i]
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    del self._tasks[task_id]
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"🧹 Otomatik temizleme: {removed_count} eski görev silindi")
            
            self._last_cleanup_time = current_time
    
    def clear_completed_tasks(self) -> int:
        """
        Tamamlanan görevleri temizle
        
        Returns:
            int: Temizlenen görev sayısı
        """
        with self._task_lock:
            completed_ids = [
                task_id for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            ]
            
            for task_id in completed_ids:
                del self._tasks[task_id]
            
            logger.info(f"🧹 {len(completed_ids)} tamamlanan görev temizlendi")
            return len(completed_ids)
    
    def get_queue_size(self) -> int:
        """
        Kuyruk boyutunu al
        
        Returns:
            int: Kuyruk boyutu
        """
        return self._task_queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Kuyruk istatistiklerini al
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self._task_lock:
            stats = {
                "queue_size": self._task_queue.qsize(),
                "total_tasks": len(self._tasks),
                "worker_count": self._worker_count,
                "running": self._running,
                "task_counts": {
                    "pending": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0
                }
            }
            
            for task in self._tasks.values():
                stats["task_counts"][task.status.value] += 1
            
            return stats


# Singleton instance
task_queue = AsyncTaskQueue()
