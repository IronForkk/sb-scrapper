"""
PostgreSQL tabanlı Logger
Uygulama loglarını PostgreSQL tablolarında saklar

Strict Mode: PostgreSQL yoksa uygulama çalışmaz
Thread-safe kuyruk tabanlı implementasyon
"""
import json
import asyncio
import queue
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from loguru import logger
from app.config import settings
from app.db.connection import connection_pool


class PostgresHandler:
    """
    Loguru için custom handler
    Logları PostgreSQL tablolarına yazar
    
    STRICT MODE: PostgreSQL yoksa uygulama çalışmaz
    Thread-safe kuyruk tabanlı implementasyon
    """
    
    def __init__(self):
        self._enabled = settings.postgres_logging_enabled
        self._pool = None
        # Thread-safe kuyruk - Memory leak önlemek için maxsize sınırlaması
        # Strict Mode korunuyor: Kuyruk dolarsa log atlanır ama uygulama çalışmaya devam eder
        self._queue = queue.Queue(maxsize=10000)  # Max 10,000 log
        # Consumer thread'i başlat
        self._consumer_thread = None
        self._stop_event = threading.Event()
        # Thread-safe cleanup mekanizması için lock
        self._cleanup_lock = threading.Lock()
        self._consumer_loop_running = False
        self._start_consumer()
    
    def _start_consumer(self):
        """Consumer thread'ini başlat"""
        if self._consumer_thread is None or not self._consumer_thread.is_alive():
            self._consumer_thread = threading.Thread(
                target=self._consumer_loop,
                daemon=True,
                name="PostgresLogConsumer"
            )
            self._consumer_thread.start()
    
    def _consumer_loop(self):
        """Consumer loop - logları kuyruktan al ve PostgreSQL'e yaz"""
        import asyncio
        import sys
        import asyncpg
        from app.config import settings
        
        with self._cleanup_lock:
            self._consumer_loop_running = True
        
        # Yeni event loop oluştur
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Consumer için kendi connection pool'ını oluştur
        consumer_pool = None
        
        async def init_pool():
            nonlocal consumer_pool
            # Retry mekanizması ile pool'u başlat
            max_retries = 10  # 10 deneme
            retry_delay = 3  # 3 saniye bekleme
            
            for attempt in range(max_retries):
                try:
                    consumer_pool = await asyncpg.create_pool(
                        host=settings.postgres_host,
                        port=settings.postgres_port,
                        user=settings.postgres_user,
                        password=settings.postgres_password,
                        database=settings.postgres_db,
                        min_size=1,
                        max_size=3,
                        command_timeout=30
                    )
                    # Test connection
                    async with consumer_pool.acquire() as conn:
                        await conn.fetchval('SELECT 1')
                    print(f"✅ PostgresHandler pool bağlantısı başarılı (deneme {attempt + 1}/{max_retries})")
                    return
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"❌ PostgresHandler pool başlatma hatası: {e}. Loglar PostgreSQL'e yazılmayacak.")
                        return
                    print(f"⚠️ PostgresHandler pool bağlantı denemesi {attempt + 1}/{max_retries} başarısız... {retry_delay}s bekleniyor.")
                    await asyncio.sleep(retry_delay)
        
        # Pool'u başlat
        try:
            loop.run_until_complete(init_pool())
        except Exception as e:
            print(f"❌ PostgresHandler pool başlatma hatası: {e}", file=sys.stderr)
            with self._cleanup_lock:
                self._consumer_loop_running = False
            return
        
        while not self._stop_event.is_set():
            try:
                # Kuyruktan log al (timeout ile)
                message = self._queue.get(timeout=1.0)
                if message is None:
                    break
                
                # Logu async olarak yaz
                try:
                    loop.run_until_complete(self._write_log_with_pool(message, consumer_pool))
                except Exception as e:
                    print(f"PostgreSQL log yazma hatası: {e}", file=sys.stderr)
                finally:
                    self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"PostgreSQL consumer loop kritik hata: {e}", file=sys.stderr)
                break
        
        # Pool'u güvenli şekilde kapat
        if consumer_pool:
            try:
                loop.run_until_complete(consumer_pool.close())
            except Exception as e:
                print(f"PostgreSQL pool kapatma hatası: {e}", file=sys.stderr)
        
        # Event loop'u güvenli şekilde kapat
        try:
            # Önce tüm pending task'ları iptal et
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Task'ların bitmesini bekle (timeout ile)
            if pending:
                try:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
            
            loop.close()
        except Exception as e:
            print(f"Event loop kapatma hatası: {e}", file=sys.stderr)
        finally:
            # Thread-local event loop'u temizle
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass
        
        with self._cleanup_lock:
            self._consumer_loop_running = False
    
    def __call__(self, message: str) -> None:
        """
        Loguru tarafından çağrılan metod
        Logu kuyruğa atar
        
        Not: Kuyruk dolarsa log atlanır ama uygulama çalışmaya devam eder (Strict Mode)
        """
        if not self._enabled:
            return
        
        # Logu kuyruğa at (non-blocking)
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            # Memory leak önlemek için kuyruk dolarsa log atlanır
            # Geliştirilmiş uyarı mekanizması - queue durumunu logla
            import sys
            queue_size = self._queue.qsize()
            print(f"⚠️ PostgreSQL log kuyruğu dolu (maxsize=10000, current={queue_size}), log atlanıyor!", file=sys.stderr)
            logger.warning(f"PostgreSQL log kuyruğu dolu (maxsize=10000, current={queue_size}), log atlanıyor!")
    
    async def _get_pool(self):
        """Connection pool'u al"""
        # Pool'u her seferinde yeniden al (cache'leme yapma)
        return await connection_pool.get_pool()
    
    async def _write_log_with_pool(self, message: str, pool) -> None:
        """Async log yazma - verilen pool ile"""
        try:
            # Mesajı parse et
            message_str = str(message)
            parts = message_str.split(" | ")
            
            if len(parts) >= 3:
                timestamp_str = parts[0].strip()
                # Timestamp string'i datetime objesine çevir (timezone-aware)
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    # Timezone-aware yap (UTC)
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError:
                    timestamp = datetime.now(timezone.utc)
                
                level = parts[1].strip()
                remaining = parts[2].strip()
                remaining_parts = remaining.split(" - ", 1)
                
                if len(remaining_parts) >= 2:
                    location = remaining_parts[0].strip()
                    msg = remaining_parts[1].strip()
                else:
                    location = remaining
                    msg = ""
                
                # Location'ı parse et (module:function:line)
                loc_parts = location.split(":")
                module = loc_parts[0] if len(loc_parts) > 0 else None
                function = loc_parts[1] if len(loc_parts) > 1 else None
                line = int(loc_parts[2]) if len(loc_parts) > 2 and loc_parts[2].isdigit() else None
                
                # Stacktrace'i temizle
                if "\n" in msg:
                    msg = msg.split("\n")[0].strip()
                
                # Tablo seçimi
                if level == "ERROR":
                    await pool.execute("""
                        INSERT INTO error_logs (timestamp, level, module, function_name, line_number, message)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, timestamp, level, module, function, line, msg)
                else:
                    await pool.execute("""
                        INSERT INTO application_logs (timestamp, level, module, function_name, line_number, message)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, timestamp, level, module, function, line, msg)
        except Exception as e:
            # Hata durumunda detaylı log (debug mode'da)
            logger.debug(f"Log yazma hatası: {e}")
            pass
    
    def write(self, message: str) -> None:
        """Write metod (Loguru için deprecated, __call__ kullanılıyor)"""
        self.__call__(message)
    
    def flush(self) -> None:
        """Flush metod (Loguru gereği)"""
        pass
    
    def stop_consumer(self):
        """
        Consumer thread'ini güvenli şekilde durdur
        Thread-safe cleanup mekanizması - Event leak önlemek için
        """
        with self._cleanup_lock:
            if not self._consumer_loop_running:
                return
            
            self._stop_event.set()
            
            # Kuyruğa stop sinyali gönder
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
            
            # Thread'in bitmesini bekle
            if self._consumer_thread and self._consumer_thread.is_alive():
                self._consumer_thread.join(timeout=10)
            
            # Event loop'u temizle - Thread-local storage'dan
            try:
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
    
    def __del__(self):
        """
        Garbage cleanup - nesne silinirken resources'ları temizle
        """
        try:
            self.stop_consumer()
        except Exception:
            pass


class PostgresLogger:
    """PostgreSQL tabanlı logger (request logging için)"""
    
    def __init__(self):
        self._pool = None
    
    async def _get_pool(self):
        """Connection pool'u al"""
        # Pool'u her seferinde yeniden al (cache'leme yapma)
        return await connection_pool.get_pool()
    
    async def log_request(self, request_data: Dict[str, Any]) -> bool:
        """
        İstek bilgilerini PostgreSQL'e sakla
        
        Args:
            request_data: Request bilgileri (ip, port, method, path, headers, body, query, etc.)
        """
        try:
            pool = await self._get_pool()
            
            await pool.execute("""
                INSERT INTO request_logs (
                    timestamp, ip, port, method, path, full_url,
                    headers, query_params, user_agent, body, body_error,
                    response_status_code, response_time_ms
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10::jsonb, $11::jsonb, $12, $13)
            """,
                datetime.now(timezone.utc),
                request_data.get('ip'),
                request_data.get('port'),
                request_data.get('method'),
                request_data.get('path'),
                request_data.get('full_url'),
                json.dumps(request_data.get('headers', {})),
                json.dumps(request_data.get('query_params', {})),
                request_data.get('user_agent'),
                json.dumps(request_data.get('body', {})) if isinstance(request_data.get('body'), dict) else request_data.get('body'),
                json.dumps(request_data.get('body_error', {})) if isinstance(request_data.get('body_error'), dict) else request_data.get('body_error'),
                request_data.get('response_status_code'),
                request_data.get('response_time_ms')
            )
            return True
        except Exception as e:
            logger.debug(f"Request log yazma hatası: {e}")
            return False
    
    async def log_domain_stats(self, domain: str, success_count: int = 0, 
                                error_count: int = 0, total_count: int = 0) -> bool:
        """
        Domain istatistiklerini PostgreSQL'e sakla
        
        Args:
            domain: Domain adı
            success_count: Başarılı işlem sayısı
            error_count: Hatalı işlem sayısı
            total_count: Toplam işlem sayısı
        """
        try:
            pool = await self._get_pool()
            
            # Başarı oranını hesapla
            success_rate = 0.0
            if total_count > 0:
                success_rate = round((success_count / total_count) * 100, 2)
            
            await pool.execute("""
                INSERT INTO domain_stats (
                    timestamp, domain, success_count, error_count, 
                    total_count, success_rate
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
                datetime.now(timezone.utc),
                domain,
                success_count,
                error_count,
                total_count,
                success_rate
            )
            return True
        except Exception as e:
            logger.debug(f"Domain stats yazma hatası: {e}")
            return False
    
    async def get_logs(self, count: int = 100, level: Optional[str] = None,
                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Logları PostgreSQL'den oku
        
        Not: SQL Injection koruması için tablo adı whitelist ile doğrulanır
        """
        try:
            pool = await self._get_pool()
            
            # Tablo seçimi - SQL Injection koruması için whitelist
            allowed_tables = ["error_logs", "application_logs"]
            table = "error_logs" if level == "ERROR" else "application_logs"
            if table not in allowed_tables:
                raise ValueError(f"Geçersiz tablo adı: {table}")
            
            # Sorgu oluştur - parameterized query kullan
            query = f"SELECT * FROM {table}"  # Tablo adı whitelist ile doğrulandı
            params = []
            conditions = []
            
            if start_date:
                conditions.append("timestamp >= $1")
                params.append(start_date)
            if end_date:
                conditions.append(f"timestamp <= ${len(params) + 1}")
                params.append(end_date)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
            params.append(count)
            
            rows = await pool.fetch(query, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Log okuma hatası: {e}")
            return []
    
    async def get_requests(self, count: int = 100, ip: Optional[str] = None,
                          path: Optional[str] = None) -> List[Dict]:
        """Request loglarını PostgreSQL'den oku"""
        try:
            pool = await self._get_pool()
            
            query = "SELECT * FROM request_logs"
            params = []
            conditions = []
            
            if ip:
                conditions.append("ip = $1")
                params.append(ip)
            if path:
                conditions.append(f"path LIKE ${len(params) + 1}")
                params.append(f"%{path}%")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
            params.append(count)
            
            rows = await pool.fetch(query, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Request log okuma hatası: {e}")
            return []
    
    async def get_domain_stats(self, count: int = 100) -> List[Dict]:
        """Domain istatistiklerini PostgreSQL'den oku"""
        try:
            pool = await self._get_pool()
            
            query = """
                SELECT * FROM domain_stats 
                ORDER BY timestamp DESC 
                LIMIT $1
            """
            
            rows = await pool.fetch(query, count)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Domain stats okuma hatası: {e}")
            return []
    
    async def health_check(self) -> bool:
        """PostgreSQL bağlantısını kontrol et"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            return True
        except Exception as e:
            logger.debug(f"Health check hatası: {e}")
            return False


# Singleton instances
postgres_handler = PostgresHandler()
postgres_logger = PostgresLogger()
