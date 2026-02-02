# SB-Scraper Architecture Documentation

## Overview

SB-Scraper, SeleniumBase tabanlı profesyonel bir web scraping API platformudur. FastAPI kullanılarak geliştirilmiş olup PostgreSQL ile loglama ve istatistik takibi yapar.

## Project Structure

```
sb-scrapper/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Konfigürasyon yönetimi (Pydantic)
│   ├── main.py                   # FastAPI ana uygulaması
│   ├── schemas.py                # Pydantic modelleri
│   ├── swagger_config.py          # Swagger UI özelleştirmesi
│   ├── core/
│   │   ├── __init__.py
│   │   ├── blacklist.py          # Black-list domain yönetimi
│   │   ├── browser.py            # SeleniumBase browser yöneticisi (Singleton)
│   │   ├── logger.py            # Loguru logger konfigürasyonu
│   │   └── postgres_logger.py    # PostgreSQL log handler (Thread-safe)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py         # asyncpg connection pool
│   │   └── models.py            # PostgreSQL tablo modelleri
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── request_tracker.py   # Request/response logging middleware
│   ├── payloads/
│   │   ├── __init__.py
│   │   ├── noise_js.py          # Canvas fingerprinting noise
│   │   └── sentinel_js.py        # JS sentinel for bot detection
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── queue.py             # Async task queue (Singleton)
│   └── utils/
│       ├── __init__.py
│       ├── memory_monitor.py     # Memory usage monitoring
│       ├── monitor.py            # System resource monitoring
│       └── user_agents.py       # User agent rotasyonu
├── log-viewer/                 # Flask log viewer uygulaması
│   ├── app.py
│   ├── db_pool.py
│   ├── Dockerfile
│   └── requirements.txt
├── migrations/                  # PostgreSQL migration dosyaları
├── static/                      # Swagger UI CSS
├── .env.example                 # Örnek konfigürasyon
├── docker-compose.yml            # Docker Compose konfigürasyonu
├── Dockerfile                   # Ana uygulama Dockerfile'ı
└── requirements.txt             # Python bağımlılıkları
```

## Core Components

### 1. BrowserManager (Singleton Pattern)

**File:** `app/core/browser.py`

Thread-safe singleton pattern kullanılarak tarayıcı yönetimi yapar.

**Özellikler:**
- SeleniumBase Driver ile Chrome tarayıcı kontrolü
- User Agent rotasyonu
- Canvas fingerprinting (noise injection)
- JS sentinel ile bot tespitinden kaçınma
- Thread-safe singleton pattern (double-checked locking)

**Kullanım:**
```python
from app.core.browser import BrowserManager

mgr = BrowserManager()  # Singleton instance
# Tarayıcı otomatik başlatılır
```

### 2. PostgresHandler (Thread-safe Logger)

**File:** `app/core/postgres_logger.py`

Loguru için custom handler. Logları PostgreSQL tablolarına yazar.

**Özellikler:**
- Thread-safe kuyruk tabanlı implementasyon
- Consumer thread ile async log yazma
- Connection pool yönetimi
- Graceful shutdown desteği

**Tablolar:**
- `application_logs` - Genel loglar
- `error_logs` - Hata logları
- `request_logs` - HTTP istek logları
- `domain_stats` - Domain istatistikleri

### 3. AsyncTaskQueue (Singleton Pattern)

**File:** `app/tasks/queue.py`

Arka planda çalışan görevler için asenkron kuyruk.

**Özellikler:**
- Thread-safe singleton pattern
- Worker thread'ler ile task işleme
- Retry mekanizması
- Otomatik task temizleme
- Graceful shutdown desteği

**Kullanım:**
```python
from app.tasks import task_queue

task_queue.start(worker_count=2)
task_id = task_queue.submit(my_function, "Task Name", args=(arg1, arg2))
```

### 4. BlacklistManager

**File:** `app/core/blacklist.py`

Domain black-list yönetimi.

**Özellikler:**
- Dosyadan black-list yükleme
- URL ve domain kontrolü
- Subdomain kontrolü (parent domain'leri de kontrol eder)
- Singleton pattern (global instance)

**Kullanım:**
```python
from app.core.blacklist import blacklist_manager

if blacklist_manager.is_blacklisted("https://example.com"):
    print("Domain black-list'te!")
```

### 5. Request Tracker Middleware

**File:** `app/middleware/request_tracker.py`

Her HTTP isteğini detaylı şekilde loglar.

**Loglanan Bilgiler:**
- IP, Port
- Method, Path
- Headers (sensitive'ler filtrelenmiş)
- Query Parameters
- Request Body (truncate edilmiş)
- Response Status Code
- Response Time

**Sensitive Headers:**
- authorization, proxy-authorization, cookie
- x-api-key, x-auth-token, token
- session-id, csrf-token
- password, secret, private-key

## Anti-Bot Detection

### Canvas Fingerprinting

**File:** `app/payloads/noise_js.py`

Canvas API'ye noise ekleyerek fingerprinting'i engeller.

**Özellikler:**
- Per-pixel noise injection
- Tutarlı noise değerleri (session bazlı)
- WebGL fingerprinting

### JS Sentinel

**File:** `app/payloads/sentinel_js.py`

Bot tespit sistemlerini engellemek için JavaScript payload'ı.

**Özellikler:**
- Navigator API manipülasyonu
- WebDriver tespitini gizleme
- Chrome object simülasyonu
- MutationObserver ile DOM değişikliklerini izleme

## Monitoring

### Memory Monitor

**File:** `app/utils/memory_monitor.py`

Bellek kullanımını izler ve threshold aşılırsa cleanup yapar.

**Özellikler:**
- Per-bucket bellek izleme
- Otomatik cleanup callback'leri
- Graceful shutdown desteği

### System Monitor

**File:** `app/utils/monitor.py`

Sistem kaynaklarını izler.

**Özellikler:**
- CPU kullanımı
- Disk kullanımı (/tmp)
- Process monitoring
- Otomatik cleanup callback'leri

## Configuration

**File:** `app/config.py`

Pydantic BaseSettings kullanılarak konfigürasyon yönetimi.

**Özellikler:**
- .env dosyasından okuma
- Validation hatalarını yakalama
- Type-safe konfigürasyon
- Default değerler

**Önemli Ayarlar:**
- `HEADLESS`: Tarayıcı headless modda çalışır
- `LOG_LEVEL`: Log seviyesi (DEBUG, INFO, WARNING, ERROR)
- `POSTGRES_*`: PostgreSQL bağlantı ayarları
- `RESPONSE_CACHING_ENABLED`: Response caching açma/kapama
- `RATE_LIMITING_ENABLED`: Rate limiting açma/kapama

## Graceful Shutdown

Uygulama kapanırken tüm kaynaklar güvenli şekilde serbest bırakılır:

1. Memory Monitor durdurulur
2. System Monitor durdurulur
3. Task Queue durdurulur (bekleyen task'ların bitmesi beklenir)
4. Browser Manager temizlenir
5. PostgreSQL Handler durdurulur
6. Connection Pool kapatılır
7. Response Cache temizlenir

## Health Check

**Endpoint:** `/health`

Tüm servislerin durumunu kontrol eder:

- PostgreSQL bağlantısı
- Browser Manager (Chrome driver)
- Task Queue
- Memory Monitor
- System Monitor
- Cache

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "services": {
    "postgresql": {"status": "healthy", "pool_initialized": true},
    "browser": {"status": "healthy", "driver_available": true},
    "task_queue": {"status": "healthy", "running": true, "queue_size": 0},
    "memory_monitor": {"status": "healthy", "running": true},
    "system_monitor": {"status": "healthy", "running": true},
    "cache": {"status": "healthy", "enabled": false}
  }
}
```

## API Endpoints

### Main Endpoints

- `POST /api/scrape` - Web scraping
- `GET /api/analyze` - HTML analizi
- `GET /health` - Health check
- `GET /logs` - Log okuma
- `GET /stats/requests` - Request istatistikleri

### Rate Limiting

Opsiyonel olarak slowapi kullanılarak rate limiting yapılabilir.

**Ayarlar:**
- `RATE_LIMITING_ENABLED`: Rate limiting açma/kapama
- `RATE_LIMIT_REQUESTS`: Maksimum istek sayısı
- `RATE_LIMIT_PERIOD`: Süre (saniye)

## Docker Deployment

### Services

1. **sb-scraper** - Ana FastAPI uygulaması
2. **postgres** - PostgreSQL veritabanı
3. **log-viewer** - Flask log viewer uygulaması

### Environment Variables

`.env.example` dosyasına bakın.

## Security

### Sensitive Data

- Password'lar loglanmaz
- API key'ler filtrelenir
- Request body'ler truncate edilir

### CORS

Opsiyonel olarak CORS ayarlanabilir.

**Ayarlar:**
- `CORS_ENABLED`: CORS açma/kapama
- `CORS_ORIGINS`: İzin verilen origin'ler
- `CORS_METHODS`: İzin verilen HTTP method'ları
- `CORS_HEADERS`: İzin verilen header'lar

## Performance

### Caching

Opsiyonel olarak response caching yapılabilir.

**Ayarlar:**
- `RESPONSE_CACHING_ENABLED`: Caching açma/kapama
- `RESPONSE_CACHE_TTL`: Cache TTL süresi (saniye)
- `RESPONSE_CACHE_MAX_SIZE`: Maksimum cache boyutu

### Connection Pool

PostgreSQL connection pool kullanılır.

**Ayarlar:**
- `POSTGRES_POOL_SIZE`: Pool boyutu
- `POSTGRES_MAX_OVERFLOW`: Maksimum overflow
- `POSTGRES_MAX_RETRIES`: Maksimum retry sayısı

## Troubleshooting

### Common Issues

1. **Chrome Driver Hatası**
   - Chrome driver versiyonunu kontrol edin
   - Docker ortamında `--no-sandbox` flag'i kullanın

2. **PostgreSQL Bağlantı Hatası**
   - `.env` dosyasındaki ayarları kontrol edin
   - PostgreSQL servisinin çalıştığından emin olun

3. **Memory Leak**
   - Memory Monitor threshold'larını kontrol edin
   - Task Queue worker sayısını azaltın

4. **Rate Limiting**
   - `RATE_LIMITING_ENABLED`'i kapatın veya limitleri artırın

## Development

### Running Locally

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyasını oluştur
cp .env.example .env

# Uygulamayı başlat
python -m app.main
```

### Running Tests

```bash
# Testleri çalıştır
pytest
```

### Linting

```bash
# Ruff ile kontrol et
ruff check .

# Ruff ile formatla
ruff format .
```

## License

Bu proje açık kaynak kodlu bir projedir. Lisans bilgileri için LICENSE dosyasına bakın.
