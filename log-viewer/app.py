"""
SB-Scrapper Log Viewer
PostgreSQL'teki log verilerini görselleştiren Flask uygulaması
"""
import os
import csv
import io
import json
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from flask import Flask, render_template, jsonify, request, Response, stream_with_context

# db_pool modülünü import et (log-viewer klasörü içinde)
try:
    from db_pool import get_db_cursor, execute_query, postgres_pool, get_pool_stats
except ImportError:
    # Geriye uyumlu: db_pool yoksa eski yöntemi kullan
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
    
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'sb_scrapper')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'sb_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    
    postgres_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    
    def get_db_connection():
        return postgres_pool.getconn()
    
    def release_db_connection(conn):
        postgres_pool.putconn(conn)
    
    def execute_query(query: str, params: tuple = None, fetch_all: bool = True) -> list:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())
            result = cursor.fetchall() if fetch_all else cursor.fetchone()
            
            if isinstance(result, list):
                for row in result:
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()
            elif result:
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
            
            return result if fetch_all else ([result] if result else [])
        except Exception as e:
            print(f"Query hatası: {e}")
            return []
        finally:
            # Connection'ı her durumda temizle (connection leak önlemek için)
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    release_db_connection(conn)
                except Exception:
                    pass
    
    def get_pool_stats() -> dict:
        try:
            return {
                'minconn': postgres_pool.minconn,
                'maxconn': postgres_pool.maxconn,
                'closed': postgres_pool.closed
            }
        except Exception as e:
            return {'error': str(e)}
    
    from contextlib import contextmanager
    @contextmanager
    def get_db_cursor():
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()

app = Flask(__name__)

# PostgreSQL bağlantı ayarları
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'sb_scrapper')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'sb_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
LOG_VIEWER_PORT = int(os.getenv('LOG_VIEWER_PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
STATS_LIMIT = int(os.getenv('STATS_LIMIT', 1000))
EXPORT_LIMIT = int(os.getenv('EXPORT_LIMIT', 5000))
LIVE_METRICS_HOURS = int(os.getenv('LIVE_METRICS_HOURS', 1))


def calculate_stats() -> Dict[str, Any]:
    """
    İstatistikleri hesaplar (N+1 Query düzeltmesi - Tek sorgu ile optimize)
    
    Returns:
        İstatistik sözlüğü:
        - total_requests: Toplam istek sayısı (healthcheck hariç)
        - error_rate: Hata oranı (%)
        - top_ips: En çok istek yapan IP'ler
        - total_logs: Toplam log sayısı
        - total_errors: Toplam hata sayısı
    """
    try:
        healthcheck_paths = ['/health', '/healthz', '/api/health', '/health-check']
        
        # Tek sorgu ile tüm istatistikleri al (N+1 düzeltmesi)
        stats = execute_query(
            """
            SELECT
                (SELECT COUNT(*) FROM application_logs) as total_logs,
                (SELECT COUNT(*) FROM error_logs) as total_errors,
                (SELECT COUNT(*) FROM request_logs WHERE path NOT IN %s) as total_requests
            """,
            (tuple(healthcheck_paths),)
        )[0]
        
        total_logs = stats['total_logs']
        total_errors = stats['total_errors']
        total_requests = stats['total_requests']
        
        # Hata oranı hesapla
        error_rate = 0.0
        if total_logs + total_errors > 0:
            error_rate = round((total_errors / (total_logs + total_errors)) * 100, 2)
        
        # Top IP'leri hesapla
        top_ips = []
        if total_requests > 0:
            top_ips = execute_query(
                """
                SELECT ip, COUNT(*) as count
                FROM request_logs
                WHERE path NOT IN %s
                GROUP BY ip
                ORDER BY count DESC
                LIMIT 5
                """,
                (tuple(healthcheck_paths),)
            )
        
        return {
            'total_requests': total_requests,
            'total_logs': total_logs,
            'total_errors': total_errors,
            'error_rate': error_rate,
            'top_ips': top_ips
        }
    except Exception as e:
        print(f"İstatistik hesaplama hatası: {e}")
        return {
            'total_requests': 0,
            'total_logs': 0,
            'total_errors': 0,
            'error_rate': 0.0,
            'top_ips': []
        }


def calculate_domain_stats() -> List[Dict[str, Any]]:
    """
    Domain bazlı başarı istatistiklerini hesaplar
    
    Returns:
        Domain istatistikleri listesi
    """
    try:
        stats = execute_query(
            """
            SELECT 
                domain,
                SUM(total_count) as total,
                SUM(success_count) as success,
                SUM(error_count) as error,
                AVG(success_rate) as success_rate
            FROM domain_stats
            GROUP BY domain
            ORDER BY total DESC
            LIMIT 100
            """
        )
        
        # Success rate'i yuvarla
        for stat in stats:
            if stat['success_rate'] is not None:
                stat['success_rate'] = round(float(stat['success_rate']), 1)
            else:
                stat['success_rate'] = 0.0
        
        return stats
    except Exception as e:
        print(f"Domain stats hesaplama hatası: {e}")
        return []


def calculate_network_status() -> Dict[str, int]:
    """
    Request loglarından status kodlarının dağılımını hesaplar
    
    Returns:
        Durum kodlarına göre dağılım sözlüğü
    """
    try:
        status_distribution = {
            '200': 0,
            '403': 0,
            '404': 0,
            '500': 0,
            'other': 0
        }
        
        # Request loglarından status kodlarını al
        results = execute_query(
            """
            SELECT response_status_code, COUNT(*) as count 
            FROM request_logs 
            WHERE response_status_code IS NOT NULL
            GROUP BY response_status_code
            """
        )
        
        for row in results:
            status_code = str(row['response_status_code'])
            count = row['count']
            
            if status_code == '200':
                status_distribution['200'] += count
            elif status_code == '403':
                status_distribution['403'] += count
            elif status_code == '404':
                status_distribution['404'] += count
            elif status_code == '500':
                status_distribution['500'] += count
            else:
                status_distribution['other'] += count
        
        return status_distribution
    except Exception as e:
        print(f"Network status hesaplama hatası: {e}")
        return {'200': 0, '403': 0, '404': 0, '500': 0, 'other': 0}


def calculate_live_metrics() -> Dict[str, Any]:
    """
    Son N saatteki canlı metrikleri hesaplar
    
    Returns:
        Canlı metrikler sözlüğü
    """
    try:
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=LIVE_METRICS_HOURS)
        
        # Son N saatteki logları al
        logs = execute_query(
            """
            SELECT COUNT(*) as count 
            FROM application_logs 
            WHERE timestamp >= %s
            """,
            (threshold_time,)
        )[0]['count']
        
        errors = execute_query(
            """
            SELECT COUNT(*) as count 
            FROM error_logs 
            WHERE timestamp >= %s
            """,
            (threshold_time,)
        )[0]['count']
        
        total_operations = logs + errors
        error_rate = round((errors / total_operations * 100), 2) if total_operations > 0 else 0.0
        
        return {
            'total_operations': total_operations,
            'error_count': errors,
            'error_rate': error_rate,
            'avg_duration': 0.0,  # PostgreSQL'de duration alanı yok
            'time_range_hours': LIVE_METRICS_HOURS
        }
    except Exception as e:
        print(f"Live metrics hesaplama hatası: {e}")
        return {
            'total_operations': 0,
            'error_count': 0,
            'error_rate': 0.0,
            'avg_duration': 0.0,
            'time_range_hours': LIVE_METRICS_HOURS
        }


def cluster_errors() -> List[Dict[str, Any]]:
    """
    Hata loglarını kümeleyerek en sık hataları bulur
    
    Returns:
        Hata kümeleri listesi
    """
    try:
        # En sık tekrar eden hataları bul
        results = execute_query(
            """
            SELECT 
                message,
                COUNT(*) as count
            FROM error_logs
            GROUP BY message
            ORDER BY count DESC
            LIMIT 5
            """
        )
        
        # Mesajları kısalt
        clusters = []
        for row in results:
            message = row['message']
            if len(message) > 100:
                message = message[:100] + '...'
            clusters.append({
                'message': message,
                'count': row['count']
            })
        
        return clusters
    except Exception as e:
        print(f"Error clustering hatası: {e}")
        return []


@app.route('/')
def index():
    """Dashboard sayfası"""
    return render_template('index.html')


@app.route('/api/logs')
def api_logs():
    """
    Logları getir (UNION ALL ile optimize edilmiş)
    
    Query params:
        - level: 'INFO', 'ERROR' veya 'ALL' (varsayılan: 'ALL')
        - limit: Maksimum kayıt sayısı (varsayılan: 100)
        - module: Modül filtresi (opsiyonel)
        - search: Mesaj içinde arama (opsiyonel)
    """
    level = request.args.get('level', 'ALL').upper()
    limit = min(int(request.args.get('limit', 100)), 1000)
    module = request.args.get('module')
    search = request.args.get('search')
    
    # WHERE koşulları için parametreler
    params = []
    conditions = []
    
    if module:
        conditions.append("module = %s")
        params.append(module)
    
    if search:
        conditions.append("message LIKE %s")
        params.append(f"%{search}%")
    
    where_clause = " AND " + " AND ".join(conditions) if conditions else ""
    
    try:
        with get_db_cursor() as cursor:
            if level == 'ALL':
                # UNION ALL ile tek sorguda veri çek
                query = f"""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM application_logs
                    WHERE timestamp >= NOW() - INTERVAL '7 days'{where_clause}
                    UNION ALL
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM error_logs
                    WHERE timestamp >= NOW() - INTERVAL '7 days'{where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(query, tuple(params))
                logs = cursor.fetchall()
            elif level == 'INFO':
                query = f"""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM application_logs
                    WHERE timestamp >= NOW() - INTERVAL '7 days'{where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(query, tuple(params))
                logs = cursor.fetchall()
            else:  # ERROR
                query = f"""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM error_logs
                    WHERE timestamp >= NOW() - INTERVAL '7 days'{where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(query, tuple(params))
                logs = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


@app.route('/api/errors')
def api_errors():
    """
    Hata loglarını getir
    
    Query params:
        - limit: Maksimum kayıt sayısı (varsayılan: 100)
    """
    limit = min(int(request.args.get('limit', 100)), 1000)
    
    errors = execute_query(
        """
        SELECT 
            timestamp, level, module, function_name, line_number, 
            message, stack_trace, url, domain
        FROM error_logs
        ORDER BY timestamp DESC
        LIMIT %s
        """,
        (limit,)
    )
    
    return jsonify({
        'success': True,
        'data': errors,
        'count': len(errors)
    })


@app.route('/api/requests')
def api_requests():
    """
    İstek loglarını getir
    
    Query params:
        - limit: Maksimum kayıt sayısı (varsayılan: 100)
        - ip: IP adresi filtresi
        - path: Path filtresi
    """
    limit = min(int(request.args.get('limit', 100)), 1000)
    ip = request.args.get('ip')
    path = request.args.get('path')
    
    query = """
        SELECT 
            timestamp, ip, port, method, path, full_url,
            headers, query_params, user_agent, body, body_error,
            response_status_code, response_time_ms
        FROM request_logs
    """
    params = []
    conditions = []
    
    if ip:
        conditions.append("ip = %s")
        params.append(ip)
    if path:
        conditions.append("path LIKE %s")
        params.append(f"%{path}%")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)
    
    requests = execute_query(query, tuple(params))
    
    # JSONB alanları zaten dict olarak döner, parse gerekmez
    # Ancak string olarak dönerse parse et
    for req in requests:
        if req.get('headers') and isinstance(req.get('headers'), str):
            try:
                req['headers'] = json.loads(req['headers'])
            except:
                pass
        if req.get('query_params') and isinstance(req.get('query_params'), str):
            try:
                req['query_params'] = json.loads(req['query_params'])
            except:
                pass
    
    return jsonify({
        'success': True,
        'data': requests,
        'count': len(requests)
    })


@app.route('/api/stats')
def api_stats():
    """İstatistikleri getir"""
    stats = calculate_stats()
    
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/health')
def api_health():
    """Gelişmiş health check endpoint'i"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT 1')
            
        # Pool istatistiklerini al
        pool_stats = get_pool_stats()
        
        # Log sayılarını al
        total_logs = execute_query(
            "SELECT COUNT(*) as count FROM application_logs"
        )[0]['count']
        
        total_errors = execute_query(
            "SELECT COUNT(*) as count FROM error_logs"
        )[0]['count']
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'postgres': 'connected',
            'pool_stats': pool_stats,
            'total_logs': total_logs,
            'total_errors': total_errors
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'postgres': 'disconnected',
            'error': str(e)
        }), 500


@app.route('/api/domain-stats')
def api_domain_stats():
    """Domain başarı tablosunu getir"""
    stats = calculate_domain_stats()
    
    return jsonify({
        'success': True,
        'data': stats,
        'count': len(stats)
    })


@app.route('/api/network-status')
def api_network_status():
    """Request loglarından status kodlarının dağılımını getir"""
    stats = calculate_network_status()
    
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/error-clusters')
def api_error_clusters():
    """Hata kümelerini getir"""
    clusters = cluster_errors()
    
    return jsonify({
        'success': True,
        'data': clusters,
        'count': len(clusters)
    })


@app.route('/api/live-metrics')
def api_live_metrics():
    """Canlı metrikleri getir (son N saat)"""
    metrics = calculate_live_metrics()
    
    return jsonify({
        'success': True,
        'data': metrics
    })


@app.route('/api/errors-table')
def api_errors_table():
    """
    Hataları URL ve mesaj şeklinde getir (Cursor-based pagination)
    
    Query params:
        - limit: Maksimum kayıt sayısı (varsayılan: 10)
        - cursor: Son kaydın timestamp'i (opsiyonel, varsayılan: None)
        - direction: 'next' veya 'prev' (varsayılan: 'next')
    
    Returns:
        - url: Hata oluşan URL
        - message: Hata mesajı
        - timestamp: Zaman damgası
        - next_cursor: Sonraki sayfa için cursor
        - prev_cursor: Önceki sayfa için cursor
    """
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        cursor = request.args.get('cursor')
        direction = request.args.get('direction', 'next')
        
        # Cursor-based pagination
        if cursor and direction == 'next':
            # Sonraki sayfa (daha eski kayıtlar)
            errors = execute_query(
                """
                SELECT
                    timestamp, message, url
                FROM error_logs
                WHERE url IS NOT NULL AND url != '' AND timestamp < %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (cursor, limit)
            )
        elif cursor and direction == 'prev':
            # Önceki sayfa (daha yeni kayıtlar)
            errors = execute_query(
                """
                SELECT
                    timestamp, message, url
                FROM error_logs
                WHERE url IS NOT NULL AND url != '' AND timestamp > %s
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (cursor, limit)
            )
            # Sonuçları yeniden eskiye çevir
            errors = list(reversed(errors))
        else:
            # İlk sayfa
            errors = execute_query(
                """
                SELECT
                    timestamp, message, url
                FROM error_logs
                WHERE url IS NOT NULL AND url != ''
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,)
            )
        
        # Cursor'ları hesapla
        next_cursor = errors[-1]['timestamp'] if errors else None
        prev_cursor = errors[0]['timestamp'] if errors and cursor else None
        
        # Toplam sayı (önbellek için)
        total = execute_query(
            "SELECT COUNT(*) as count FROM error_logs WHERE url IS NOT NULL AND url != ''"
        )[0]['count']
        
        return jsonify({
            'success': True,
            'data': errors,
            'count': len(errors),
            'total': total,
            'next_cursor': next_cursor,
            'prev_cursor': prev_cursor if cursor else None,
            'limit': limit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Veriler yüklenirken hata oluştu',
            'data': []
        }), 500


@app.route('/api/success-table')
def api_success_table():
    """
    Başarılı işlemleri URL ve durum şeklinde getir (Cursor-based pagination)
    
    Query params:
        - limit: Maksimum kayıt sayısı (varsayılan: 10)
        - cursor: Son kaydın timestamp'i (opsiyonel, varsayılan: None)
        - direction: 'next' veya 'prev' (varsayılan: 'next')
    
    Returns:
        - url: İşlem yapılan URL
        - status: Başarı durumu
        - timestamp: Zaman damgası
        - next_cursor: Sonraki sayfa için cursor
        - prev_cursor: Önceki sayfa için cursor
    """
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        cursor = request.args.get('cursor')
        direction = request.args.get('direction', 'next')
        
        # Cursor-based pagination
        if cursor and direction == 'next':
            # Sonraki sayfa (daha eski kayıtlar)
            requests_data = execute_query(
                """
                SELECT
                    timestamp, path, response_status_code
                FROM request_logs
                WHERE response_status_code >= 200 AND response_status_code < 300 AND timestamp < %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (cursor, limit)
            )
        elif cursor and direction == 'prev':
            # Önceki sayfa (daha yeni kayıtlar)
            requests_data = execute_query(
                """
                SELECT
                    timestamp, path, response_status_code
                FROM request_logs
                WHERE response_status_code >= 200 AND response_status_code < 300 AND timestamp > %s
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (cursor, limit)
            )
            # Sonuçları yeniden eskiye çevir
            requests_data = list(reversed(requests_data))
        else:
            # İlk sayfa
            requests_data = execute_query(
                """
                SELECT
                    timestamp, path, response_status_code
                FROM request_logs
                WHERE response_status_code >= 200 AND response_status_code < 300
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,)
            )
        
        # Cursor'ları hesapla
        next_cursor = requests_data[-1]['timestamp'] if requests_data else None
        prev_cursor = requests_data[0]['timestamp'] if requests_data and cursor else None
        
        # Toplam sayı (önbellek için)
        total = execute_query(
            """
            SELECT COUNT(*) as count
            FROM request_logs
            WHERE response_status_code >= 200 AND response_status_code < 300
            """
        )[0]['count']
        
        return jsonify({
            'success': True,
            'data': requests_data,
            'count': len(requests_data),
            'total': total,
            'next_cursor': next_cursor,
            'prev_cursor': prev_cursor if cursor else None,
            'limit': limit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Veriler yüklenirken hata oluştu',
            'data': []
        }), 500


@app.route('/api/export/csv')
def api_export_csv():
    """Tüm verileri CSV formatında dışa aktarır"""
    try:
        # Verileri topla
        logs = execute_query(
            """
            SELECT 
                timestamp, level, module, function_name, line_number, message
            FROM application_logs
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (EXPORT_LIMIT,)
        )
        
        errors = execute_query(
            """
            SELECT 
                timestamp, level, module, function_name, line_number, 
                message, url, domain
            FROM error_logs
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (EXPORT_LIMIT,)
        )
        
        requests_data = execute_query(
            """
            SELECT 
                timestamp, ip, port, method, path, full_url,
                user_agent, response_status_code, response_time_ms
            FROM request_logs
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (EXPORT_LIMIT,)
        )
        
        domain_stats = calculate_domain_stats()
        network_status = calculate_network_status()
        
        # CSV oluştur
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Başlık
        writer.writerow(['SB-Scrapper Analytics Export'])
        writer.writerow([f'Export Date: {datetime.now(timezone.utc).isoformat()}'])
        writer.writerow([])
        
        # Domain Stats
        writer.writerow(['=== DOMAIN STATS ==='])
        writer.writerow(['Domain', 'Total', 'Success', 'Error', 'Success Rate'])
        for stat in domain_stats:
            writer.writerow([
                stat['domain'],
                stat['total'],
                stat['success'],
                stat['error'],
                f"{stat['success_rate']}%"
            ])
        writer.writerow([])
        
        # Network Status
        writer.writerow(['=== NETWORK STATUS ==='])
        writer.writerow(['Status Code', 'Count'])
        for status, count in network_status.items():
            writer.writerow([status, count])
        writer.writerow([])
        
        # Logs
        writer.writerow(['=== LOGS ==='])
        writer.writerow(['Timestamp', 'Level', 'Module', 'Function', 'Line', 'Message'])
        for log in logs[:EXPORT_LIMIT]:
            writer.writerow([
                log.get('timestamp', ''),
                log.get('level', ''),
                log.get('module', ''),
                log.get('function_name', ''),
                log.get('line_number', ''),
                log.get('message', '')
            ])
        writer.writerow([])
        
        # Errors
        writer.writerow(['=== ERRORS ==='])
        writer.writerow(['Timestamp', 'Module', 'Function', 'Line', 'Message', 'URL', 'Domain'])
        for error in errors[:EXPORT_LIMIT]:
            writer.writerow([
                error.get('timestamp', ''),
                error.get('module', ''),
                error.get('function_name', ''),
                error.get('line_number', ''),
                error.get('message', ''),
                error.get('url', ''),
                error.get('domain', '')
            ])
        
        # Response oluştur
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=sb-scrapper-export-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.csv'
            }
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'CSV export sırasında hata oluştu'
        }), 500


@app.route('/api/logs/stream')
def logs_stream():
    """
    Canlı log akışı için Polling tabanlı endpoint (SSE yerine)
    Connection pool tükenmesini önlemek için polling kullanılır
    
    Query params:
        - level: 'INFO', 'ERROR' veya 'ALL' (varsayılan: 'ALL')
        - since: Son kontrol zamanı (timestamp string)
    """
    level = request.args.get('level', 'ALL').upper()
    since_str = request.args.get('since')
    
    last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=2)
    
    if since_str:
        try:
            last_timestamp = datetime.fromisoformat(since_str)
        except:
            pass
    
    try:
        logs = []
        
        with get_db_cursor() as cursor:
            if level == 'ALL':
                cursor.execute("""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM application_logs
                    WHERE timestamp > %s
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (last_timestamp,))
                logs = cursor.fetchall()
                
                if not logs:
                    cursor.execute("""
                        SELECT
                            timestamp, level, module, function_name, line_number, message
                        FROM error_logs
                        WHERE timestamp > %s
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """, (last_timestamp,))
                    logs = cursor.fetchall()
            elif level == 'INFO':
                cursor.execute("""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM application_logs
                    WHERE timestamp > %s
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (last_timestamp,))
                logs = cursor.fetchall()
            else:  # ERROR
                cursor.execute("""
                    SELECT
                        timestamp, level, module, function_name, line_number, message
                    FROM error_logs
                    WHERE timestamp > %s
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (last_timestamp,))
                logs = cursor.fetchall()
        
        # Datetime objelerini string'e çevir
        for log in logs:
            if isinstance(log.get('timestamp'), datetime):
                log['timestamp'] = log['timestamp'].isoformat()
        
        # En son timestamp'i döndür
        next_since = datetime.now(timezone.utc).isoformat()
        
        return jsonify({
            'success': True,
            'data': logs,
            'next_since': next_since
        })
    except Exception as e:
        print(f"Log stream hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


@app.route('/api/modules')
def api_modules():
    """
    Mevcut modül listesini döndürür (filtreleme için)
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT module
                FROM application_logs
                WHERE module IS NOT NULL AND module != ''
                ORDER BY module
            """)
            modules = [row['module'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'data': modules,
            'count': len(modules)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


if __name__ == '__main__':
    # Production için DEBUG ortam değişkeninden okunur
    app.run(host='0.0.0.0', port=LOG_VIEWER_PORT, debug=DEBUG)
