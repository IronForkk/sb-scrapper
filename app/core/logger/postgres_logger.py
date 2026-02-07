"""
PostgreSQL Logger Sınıfı
Request logging ve domain stats için logger (Native Python logging)
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.logger.native_logger import logger
from app.config import settings
from app.db.connection import postgres_connection


class PostgresLogger:
    """PostgreSQL tabanlı logger (request logging için) - SENKRON"""
    
    def log_request(self, request_data: Dict[str, Any]) -> bool:
        """
        İstek bilgilerini PostgreSQL'e sakla (senkron)
        
        Args:
            request_data: Request bilgileri (ip, port, method, path, headers, body, query, etc.)
        """
        conn = None
        try:
            conn = postgres_connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO request_logs (
                    timestamp, ip, port, method, path, full_url,
                    headers, query_params, user_agent, body, body_error,
                    response_status_code, response_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
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
            )
            conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.debug(f"Request log yazma hatası: {e}")
            return False
    
    def log_domain_stats(self, domain: str, success_count: int = 0,
                        error_count: int = 0, duration: float = 0.0,
                        raw_desktop_ss: bool = False, raw_mobile_ss: bool = False,
                        main_desktop_ss: bool = False, google_ss: bool = False,
                        ddg_ss: bool = False, raw_html: bool = False,
                        google_html: bool = False, ddg_html: bool = False,
                        network_logs: bool = False) -> bool:
        """
        Domain istatistiklerini PostgreSQL'e güncelle (senkron)
        
        Args:
            domain: Domain adı
            success_count: Başarılı işlem sayısı (0 veya 1)
            error_count: Hatalı işlem sayısı (0 veya 1)
            duration: İşlem süresi (saniye)
            raw_desktop_ss: Masaüstü ekran görüntüsü alındı mı
            raw_mobile_ss: Mobil ekran görüntüsü alındı mı
            main_desktop_ss: Ana domain masaüstü ekran görüntüsü alındı mı
            google_ss: Google arama ekran görüntüsü alındı mı
            ddg_ss: DuckDuckGo arama ekran görüntüsü alındı mı
            raw_html: Ham URL HTML alındı mı
            google_html: Google HTML alındı mı
            ddg_html: DuckDuckGo HTML alındı mı
            network_logs: Network logları alındı mı
        """
        conn = None
        try:
            conn = postgres_connection.get_connection()
            cursor = conn.cursor()
            
            # Domain için mevcut kaydı kontrol et
            cursor.execute("""
                SELECT id, success_count, error_count, total_count,
                       raw_desktop_ss_count, raw_mobile_ss_count, main_desktop_ss_count,
                       google_ss_count, ddg_ss_count, raw_html_count,
                       google_html_count, ddg_html_count, network_logs_count,
                       total_duration
                FROM domain_stats
                WHERE domain = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (domain,))
            
            row = cursor.fetchone()
            
            if row:
                # Mevcut kayıt varsa güncelle
                (existing_id, existing_success, existing_error, existing_total,
                 existing_raw_desktop_ss, existing_raw_mobile_ss, existing_main_desktop_ss,
                 existing_google_ss, existing_ddg_ss, existing_raw_html,
                 existing_google_html, existing_ddg_html, existing_network_logs,
                 existing_total_duration) = row
                
                new_success = existing_success + success_count
                new_error = existing_error + error_count
                new_total = existing_total + 1
                # Decimal ve float toplama hatası önlemek için float'a çevir
                new_total_duration = float(existing_total_duration) + duration
                
                # Başarı oranını hesapla
                success_rate = 0.0
                if new_total > 0:
                    success_rate = round((new_success / new_total) * 100, 2)
                
                # Ortalama süreyi hesapla
                avg_duration = round(new_total_duration / new_total, 2) if new_total > 0 else 0.0
                
                # Ekran görüntüsü ve HTML sayaçlarını güncelle
                new_raw_desktop_ss = existing_raw_desktop_ss + (1 if raw_desktop_ss else 0)
                new_raw_mobile_ss = existing_raw_mobile_ss + (1 if raw_mobile_ss else 0)
                new_main_desktop_ss = existing_main_desktop_ss + (1 if main_desktop_ss else 0)
                new_google_ss = existing_google_ss + (1 if google_ss else 0)
                new_ddg_ss = existing_ddg_ss + (1 if ddg_ss else 0)
                new_raw_html = existing_raw_html + (1 if raw_html else 0)
                new_google_html = existing_google_html + (1 if google_html else 0)
                new_ddg_html = existing_ddg_html + (1 if ddg_html else 0)
                new_network_logs = existing_network_logs + (1 if network_logs else 0)
                
                cursor.execute("""
                    UPDATE domain_stats
                    SET timestamp = %s,
                        success_count = %s,
                        error_count = %s,
                        total_count = %s,
                        success_rate = %s,
                        raw_desktop_ss_count = %s,
                        raw_mobile_ss_count = %s,
                        main_desktop_ss_count = %s,
                        google_ss_count = %s,
                        ddg_ss_count = %s,
                        raw_html_count = %s,
                        google_html_count = %s,
                        ddg_html_count = %s,
                        network_logs_count = %s,
                        total_duration = %s,
                        avg_duration = %s
                    WHERE id = %s
                """,
                    (
                        datetime.now(timezone.utc),
                        new_success,
                        new_error,
                        new_total,
                        success_rate,
                        new_raw_desktop_ss,
                        new_raw_mobile_ss,
                        new_main_desktop_ss,
                        new_google_ss,
                        new_ddg_ss,
                        new_raw_html,
                        new_google_html,
                        new_ddg_html,
                        new_network_logs,
                        new_total_duration,
                        avg_duration,
                        existing_id
                    )
                )
            else:
                # Yeni kayıt oluştur
                total_count = success_count + error_count
                success_rate = 0.0
                if total_count > 0:
                    success_rate = round((success_count / total_count) * 100, 2)
                
                # Ortalama süreyi hesapla
                avg_duration = round(duration / total_count, 2) if total_count > 0 else 0.0
                
                cursor.execute("""
                    INSERT INTO domain_stats (
                        timestamp, domain, success_count, error_count,
                        total_count, success_rate,
                        raw_desktop_ss_count, raw_mobile_ss_count, main_desktop_ss_count,
                        google_ss_count, ddg_ss_count, raw_html_count,
                        google_html_count, ddg_html_count, network_logs_count,
                        total_duration, avg_duration
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        datetime.now(timezone.utc),
                        domain,
                        success_count,
                        error_count,
                        total_count,
                        success_rate,
                        1 if raw_desktop_ss else 0,
                        1 if raw_mobile_ss else 0,
                        1 if main_desktop_ss else 0,
                        1 if google_ss else 0,
                        1 if ddg_ss else 0,
                        1 if raw_html else 0,
                        1 if google_html else 0,
                        1 if ddg_html else 0,
                        1 if network_logs else 0,
                        duration,
                        avg_duration
                    )
                )
            
            conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.debug(f"Domain stats yazma hatası: {e}")
            return False
    
    def health_check(self) -> bool:
        """PostgreSQL bağlantısını kontrol et (senkron)"""
        conn = None
        try:
            conn = postgres_connection.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            return True
        except Exception as e:
            logger.debug(f"Health check hatası: {e}")
            return False
    
    def initialize(self) -> None:
        """
        PostgreSQL bağlantısını başlat (senkron)
        
        Raises:
            Exception: PostgreSQL bağlantı hatası
        """
        try:
            postgres_connection.initialize()
            print("✅ PostgreSQL bağlantısı başlatıldı.")
        except Exception as e:
            print(f"❌ PostgreSQL bağlantı hatası: {e}")
            raise
    
    def close(self) -> None:
        """
        PostgreSQL bağlantısını kapat (senkron)
        """
        try:
            postgres_connection.close()
            print("🔌 PostgreSQL bağlantısı kapatıldı.")
        except Exception as e:
            print(f"❌ PostgreSQL bağlantı kapatma hatası: {e}")


# Singleton instance
postgres_logger = PostgresLogger()
