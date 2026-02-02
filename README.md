<div align="center">

# 🕷️ SB-Scraper

### Profesyonel Web Scraping API Platformu

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Anti-Bot Detection Bypass | Canvas Fingerprinting Noise | Advanced Popup Removal | Request Logging | Real-time Monitoring**

</div>

---

## 📋 İçindekiler

- [🎯 Proje Hakkında](#-proje-hakkında)
- [✨ Özellikler](#-özellikler)
- [🏗️ Mimari](#-mimari)
- [🛠️ Teknoloji Yığını](#️-teknoloji-yığını)
- [📦 Kurulum](#-kurulum)
- [🚀 Kullanım](#-kullanım)
- [📊 API Dokümantasyonu](#-api-dokümantasyonu)
- [🔧 Konfigürasyon](#-konfigürasyon)
- [📈 Log Viewer](#-log-viewer)
- [🐳 Docker](#-docker)
- [📂 Proje Yapısı](#-proje-yapısı)
- [🔒 Güvenlik](#-güvenlik)

---

## 🎯 Proje Hakkında

**SB-Scraper**, SeleniumBase tabanlı, anti-bot detection bypass yetenekleri olan profesyonel bir web scraping API platformudur. Modern web sitelerini tarayarak HTML kaynak kodu, ekran görüntüsü ve arama motoru sonuçlarını toplar.

### Neden SB-Scraper?

Günümüzde web siteleri, botları tespit etmek için çeşitli yöntemler kullanmaktadır:
- **Canvas Fingerprinting**: Tarayıcıyı benzersiz bir parmak izi ile tanımlama
- **Popup ve Modal Engelleri**: İçeriği gizleyen reklam ve cookie banner'ları
- **User Agent Kontrolü**: Standart bot user agent'larını engelleme
- **Rate Limiting**: Çok fazla istek gönderen IP'leri engelleme

SB-Scraper, bu engelleri aşmak için gelişmiş teknikler kullanır:
- **Canvas Noise Injection**: Canvas fingerprinting'i bozmak için tutarlı gürültü ekler
- **JS Sentinel**: Popup, modal ve overlay'leri akıllıca temizler
- **Rastgele User Agent**: Farklı tarayıcı ve işletim sistemlerini simüle eder
- **Black-List Yönetimi**: Yasaklı domain'leri filtreler

---

## ✨ Özellikler

### 🌐 Web Scraping
- **HTML Kaynak Kodu**: Sayfanın tam HTML içeriğini alır
- **Mobil Ekran Görüntüsü**: 375x812 piksel mobil görünümde screenshot alır
- **Google Arama Sonuçları**: Siteyi Google'da aratır, sonuç ekran görüntüsü ve HTML alır
- **DuckDuckGo Arama Sonuçları**: Siteyi DuckDuckGo'da aratır, sonuç ekran görüntüsü ve HTML alır
- **Ana Domain Taraması**: Verilen URL'in ana domainini de tarar
- **Ham URL Taraması**: Verilen URL'i doğrudan tarar

### 🛡️ Anti-Bot Detection
- **Canvas Noise**: Canvas 2D ve WebGL fingerprinting'i bozar
- **Audio Noise**: Audio fingerprinting'i bozar
- **WebGL Vendor/Renderer Spoofing**: GPU bilgilerini değiştirir
- **JS Sentinel**: Popup, modal, cookie banner'larını temizler
- **Rastgele User Agent**: Windows, macOS, Linux platformları için UA seçenekleri

### 📊 Loglama ve İzleme
- **PostgreSQL Loglama**: Tüm loglar veritabanında saklanır
- **JSONB Desteği**: JSON alanları JSONB tipinde saklanır (performans optimizasyonu)
- **Request Tracking**: Her isteğin detayları (IP, headers, query params, response time) loglanır
- **Domain Stats**: Scraping istatistikleri (success/error count, success rate) takip edilir
- **Error Logging**: Hatalar ayrı bir tabloda saklanır, hızlı sorgulama için optimize edilir
- **Structured Logging**: JSON formatında loglama (opsiyonel)
- **Partitioning**: Log tabloları aylık partition'larda saklanır (büyük veri için optimizasyon)
- **Retention Policy**: Otomatik log temizleme (cron job ile)

### 🎛️ Yönetim ve İzleme
- **Log Viewer Web UI**: PostgreSQL loglarını görselleştiren Flask uygulaması
- **Canlı Güncelleme**: Polling tabanlı gerçek zamanlı log güncellemeleri
- **Gelişmiş Filtreler**: Modül, metin arama ve seviye filtreleri
- **System Monitor**: RAM/CPU kullanımını izler, otomatik temizlik yapar
- **Health Check**: [`/health`](#health-check) endpoint ile kapsamlı servis durumu kontrolü
- **Swagger UI**: Otomatik API dokümantasyonu

### 🔒 Güvenlik
- **API Key Authentication**: X-API-Key header ile doğrulama (opsiyonel)
- **Rate Limiting**: İstek sınırlama (opsiyonel)
- **CORS Support**: Cross-Origin Resource Sharing (opsiyonel)
- **Sensitive Header Filtering**: Hassas header'lar loglanmaz
- **Request Body Truncation**: Büyük request body'ler truncate edilir

---

## 🏗️ Mimari

Detaylı mimari dokümantasyonu için [`ARCHITECTURE.md`](ARCHITECTURE.md) dosyasına bakın.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client / User                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Middleware Layer                                          │  │
│  │  - Request Tracker (IP, Headers, Query, Body)            │  │
│  │  - Rate Limiting (Opsiyonel)                               │  │
│  │  - CORS (Opsiyonel)                                        │  │
│  │  - API Key Authentication (Opsiyonel)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  API Endpoints                                            │  │
│  │  - POST /scrape (Ana scraping endpoint)                   │  │
│  │  - GET /health (Health check - Kapsamlı)                  │  │
│  │  - GET /tasks (Task queue status)                         │  │
│  │  - GET /monitor (System monitor)                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Core Components                                          │  │
│  │  - BrowserManager (SeleniumBase Singleton)                │  │
│  │  - BlacklistManager (Domain filtering)                    │  │
│  │  - TaskQueue (Async task management)                      │  │
│  │  - SystemMonitor (Resource monitoring)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
 ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
 │  PostgreSQL  │    │  Chrome Browser  │    │  Log Viewer UI   │
 │              │    │  (SeleniumBase)  │    │  (Flask App)     │
 │ - app_logs   │    │ - Canvas Noise   │    │ - Dashboard      │
 │ - req_logs   │    │ - JS Sentinel    │    │ - Statistics     │
 │ - error_logs │    │ - Random UA      │    │ - Export         │
 │ - domain_    │    │ - Screenshot     │    │ - Live Metrics   │
 │   stats      │    │                  │    │                  │
 └──────────────┘    └──────────────────┘    └──────────────────┘
```

### Tasarım Desenleri

| Desen | Kullanım Alanı | Açıklama |
|-------|---------------|----------|
| **Singleton** | `BrowserManager`, `TaskQueue`, `PostgresHandler` | Tek bir instance kullanılır, thread-safe |
| **Factory** | `ConnectionPool` | Bağlantı havuzu oluşturma |
| **Middleware** | `request_tracker_middleware` | Request/response logging |
| **Observer** | `SystemMonitor` | Callback fonksiyonları ile event handling |
| **Repository** | `postgres_logger` | Veritabanı işlemleri soyutlanır |

---

## 🛠️ Teknoloji Yığını

### Backend Framework
- **FastAPI 0.109.0**: Modern, hızlı, async Python web framework
  - Otomatik API dokümantasyonu (Swagger UI)
  - Pydantic ile data validation
  - Async/await desteği
  - Type hints ile IDE desteği

### Web Scraping
- **SeleniumBase 4.46.0**: Selenium üzerine kurulu gelişmiş scraping kütüphanesi
  - Otomatik driver yönetimi
  - Visual regression testing
  - CSS/XPath selector desteği
  - Screenshot alma özelliği

### Veritabanı
- **PostgreSQL 15**: Güçlü, açık kaynaklı ilişkisel veritabanı
  - JSONB desteği (structured data için)
  - Full-text search
  - Advanced indexing
  - Timezone-aware timestamp
- **asyncpg 0.29.0**: PostgreSQL için async driver
  - High performance
  - Connection pooling
  - Prepared statements
- **psycopg2-binary 2.9.9**: Log Viewer için sync driver

### Loglama
- **Loguru 0.7.2**: Python logging kütüphanesi
  - Structured logging (JSON format)
  - Rotation ve retention
  - Custom handler desteği
  - Thread-safe

### Validation
- **Pydantic 2.5.0**: Data validation kütüphanesi
  - Type hints ile validation
  - Custom validators
  - Serialization/Deserialization
- **pydantic-settings 2.1.0**: Settings management

### Web Server
- **Uvicorn 0.27.0**: ASGI server
  - Async/await desteği
  - HTTP/1.1 ve WebSocket
  - Process/Thread management
- **Gunicorn 21.2.0**: WSGI HTTP server (production için)

### Diğer Kütüphaneler
- **requests 2.32.5**: HTTP requests
- **python-dotenv 1.0.0**: .env dosyası desteği
- **pandas 2.1.4**: Data manipulation
- **psutil 6.0.0**: System monitoring
- **memory_profiler 0.61.0**: Memory profiling

### Frontend (Log Viewer)
- **Flask**: Web framework
- **Bootstrap 5**: UI framework
- **Chart.js**: Grafik kütüphanesi
- **jQuery**: JavaScript kütüphanesi

---

## 📦 Kurulum

### Gereksinimler

- **Python 3.11+**
- **PostgreSQL 15+**
- **Docker & Docker Compose** (opsiyonel ama önerilir)

### Docker ile Kurulum (Önerilen)

1. **Projeyi klonlayın:**
```bash
git clone https://github.com/your-username/sb-scrapper.git
cd sb-scrapper
```

2. **`.env` dosyasını oluşturun:**
```bash
cp .env.example .env
```

3. **`.env` dosyasını düzenleyin:**
```bash
# PostgreSQL şifresini değiştirin
POSTGRES_PASSWORD=your_strong_password_here

# Diğer ayarları ihtiyacınıza göre düzenleyin
```

4. **Docker Compose ile başlatın:**
```bash
docker-compose up -d
```

5. **Servislerin durumunu kontrol edin:**
```bash
docker-compose ps
```

### Manuel Kurulum

1. **Python sanal ortamı oluşturun:**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate  # Windows
```

2. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Chromedriver indirin:**
```bash
seleniumbase get chromedriver --path
```

4. **PostgreSQL veritabanını oluşturun:**
```sql
CREATE DATABASE sb_scrapper;
CREATE USER sb_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sb_scrapper TO sb_user;
```

5. **Migration'ları çalıştırın:**
   ```bash
   # Migrasyonları sırayla çalıştırın
   psql -U sb_user -d sb_scrapper -f migrations/001_initial_schema.sql
   psql -U sb_user -d sb_scrapper -f migrations/002_add_indexes.sql
   psql -U sb_user -d sb_scrapper -f migrations/003_cleanup_function.sql
   psql -U sb_user -d sb_scrapper -f migrations/004_jsonb_migration.sql
   psql -U sb_user -d sb_scrapper -f migrations/005_partitioning.sql
   psql -U sb_user -d sb_scrapper -f migrations/006_retention_policy.sql
   ```

6. **Uygulamayı başlatın:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🚀 Kullanım

### API Endpoint'leri

#### 1. Web Scraping

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "wait_time": 8,
    "get_html": true,
    "get_mobile_ss": true,
    "get_google_search": true,
    "get_google_html": true,
    "get_ddg_search": true,
    "get_ddg_html": true,
    "process_raw_url": true,
    "process_main_domain": true
  }'
```

#### 2. Health Check

```bash
curl http://localhost:8000/health
```

#### 3. Task Queue Status

```bash
curl http://localhost:8000/tasks
```

#### 4. System Monitor

```bash
curl http://localhost:8000/monitor
```

### Python ile Kullanım

```python
import requests

# API endpoint
url = "http://localhost:8000/scrape"

# Request payload
payload = {
    "url": "https://example.com",
    "wait_time": 8,
    "get_html": True,
    "get_mobile_ss": True,
    "get_google_search": True,
    "get_google_html": True,
    "get_ddg_search": True,
    "get_ddg_html": True,
    "process_raw_url": True,
    "process_main_domain": True
}

# İsteği gönder
response = requests.post(url, json=payload)

# Sonucu yazdır
print(response.json())
```

### JavaScript ile Kullanım

```javascript
const response = await fetch('http://localhost:8000/scrape', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    url: 'https://example.com',
    wait_time: 8,
    get_html: true,
    get_mobile_ss: true,
    get_google_search: true,
    get_google_html: true,
    get_ddg_search: true,
    get_ddg_html: true,
    process_raw_url: true,
    process_main_domain: true
  })
});

const data = await response.json();
console.log(data);
```

---

## 📊 API Dokümantasyonu

### Swagger UI

API dokümantasyonu otomatik olarak oluşturulur:

```
http://localhost:8000/docs
```

### ReDoc

Alternatif dokümantasyon:

```
http://localhost:8000/redoc
```

### Request Schema

```python
class ScrapeRequest(BaseModel):
    # Zorunlu alanlar
    url: str  # Taranacak URL
    
    # Zaman ayarları
    wait_time: int = 8  # Bekleme süresi (saniye)
    
    # İşlem ayarları
    process_raw_url: bool = True  # Ham URL tara
    process_main_domain: bool = True  # Ana domain tara
    
    # Çıktı ayarları
    get_html: bool = True  # HTML al
    get_mobile_ss: bool = True  # Mobil screenshot al
    
    # Arama motorları
    get_google_search: bool = True  # Google arama SS al
    get_google_html: bool = True  # Google HTML al
    get_ddg_search: bool = True  # DuckDuckGo arama SS al
    get_ddg_html: bool = True  # DuckDuckGo HTML al
```

### Response Schema

```python
class ScrapeResponse(BaseModel):
    success: bool
    url: str
    domain: str
    timestamp: str
    
    # Scraping sonuçları
    html: Optional[str]  # Base64 encoded HTML
    mobile_screenshot: Optional[str]  # Base64 encoded screenshot
    
    # Arama motoru sonuçları
    google_search_screenshot: Optional[str]
    google_html: Optional[str]
    ddg_search_screenshot: Optional[str]
    ddg_html: Optional[str]
    
    # Meta bilgiler
    processing_time_ms: int
    error: Optional[str]
```

---

## 🔧 Konfigürasyon

### Environment Variables

#### Tarayıcı Ayarları

| Variable | Default | Açıklama |
|----------|---------|----------|
| `HEADLESS` | `true` | Tarayıcı headless modda çalışır |
| `WAIT_TIME` | `8` | Sayfa yüklendikten sonra bekleme süresi (saniye) |
| `USER_AGENT_PLATFORM` | `windows` | User Agent platformu (windows/macos/linux) |
| `PAGE_LOAD_TIMEOUT` | `60` | Sayfa yükleme zaman aşımı (saniye) |
| `BODY_CHECK_WAIT_TIME` | `2` | JavaScript yüklenmesi için bekleme (saniye) |
| `PAGE_RELOAD_WAIT_TIME` | `5` | Sayfa yeniden yükleme bekleme (saniye) |

#### API Ayarları

| Variable | Default | Açıklama |
|----------|---------|----------|
| `HOST` | `0.0.0.0` | API sunucusu adresi |
| `PORT` | `8000` | API sunucusu portu |

#### Loglama Ayarları

| Variable | Default | Açıklama |
|----------|---------|----------|
| `LOG_LEVEL` | `INFO` | Log seviyesi (DEBUG/INFO/WARNING/ERROR) |
| `CONSOLE_LOGGING_ENABLED` | `true` | Konsola log yazma |
| `POSTGRES_LOGGING_ENABLED` | `true` | PostgreSQL'e log yazma |
| `STRUCTURED_LOGGING_ENABLED` | `false` | JSON formatında loglama |

#### PostgreSQL Ayarları

| Variable | Default | Açıklama |
|----------|---------|----------|
| `POSTGRES_HOST` | `postgres` | PostgreSQL sunucusu adresi |
| `POSTGRES_PORT` | `5432` | PostgreSQL portu |
| `POSTGRES_DB` | `sb_scrapper` | Veritabanı adı |
| `POSTGRES_USER` | `sb_user` | Kullanıcı adı |
| `POSTGRES_PASSWORD` | - | Şifre (zorunlu) |
| `POSTGRES_POOL_SIZE` | `10` | Connection pool boyutu |
| `POSTGRES_MAX_OVERFLOW` | `20` | Maksimum overflow |
| `POSTGRES_MAX_RETRIES` | `5` | Maksimum retry sayısı |

#### Retention Policy

| Variable | Default | Açıklama |
|----------|---------|----------|
| `LOG_RETENTION_DAYS` | `30` | Log saklama süresi (gün) |
| `ERROR_RETENTION_DAYS` | `30` | Hata log saklama süresi (gün) |
| `REQUEST_RETENTION_DAYS` | `30` | Request log saklama süresi (gün) |
| `DOMAIN_STATS_RETENTION_DAYS` | `30` | Domain stats saklama süresi (gün) |

#### Canvas Noise Ayarları

| Variable | Default | Açıklama |
|----------|---------|----------|
| `NOISE_MIN_VALUE` | `-20` | Minimum gürültü değeri |
| `NOISE_MAX_VALUE` | `20` | Maksimum gürültü değeri |

#### Rate Limiting (Opsiyonel)

| Variable | Default | Açıklama |
|----------|---------|----------|
| `RATE_LIMITING_ENABLED` | `false` | Rate limiting aktif mi |
| `RATE_LIMIT_REQUESTS` | `100` | Maksimum istek sayısı |
| `RATE_LIMIT_PERIOD` | `60` | Periyot (saniye) |

#### Authentication (Opsiyonel)

| Variable | Default | Açıklama |
|----------|---------|----------|
| `AUTH_ENABLED` | `false` | API key doğrulama aktif mi |
| `AUTH_API_KEY` | - | API key (zorunlu) |

---

## 📈 Log Viewer

Log Viewer, PostgreSQL'teki log verilerini görselleştiren bir Flask uygulamasıdır.

### Özellikler

- **Dashboard**: Genel istatistikler ve metrikler
- **Application Logs**: Uygulama loglarını filtrele ve görüntüle
- **Request Logs**: Request/response loglarını görüntüle
- **Error Logs**: Hata loglarını görüntüle
- **Domain Stats**: Scraping istatistiklerini görüntüle
- **Export**: Logları CSV olarak dışa aktar
- **Live Metrics**: Canlı metrikler

### Erişim

```
http://localhost:5000
```

### API Endpoints

| Endpoint | Açıklama |
|----------|----------|
| `/api/health` | Health check |
| `/api/stats` | Genel istatistikler |
| `/api/logs` | Application logs |
| `/api/requests` | Request logs |
| `/api/errors` | Error logs |
| `/api/domain-stats` | Domain stats |
| `/api/export` | CSV export |

---

## 🐳 Docker

### Docker Compose Servisleri

#### 1. PostgreSQL
- PostgreSQL 15 Alpine
- Otomatik migration çalıştırma
- Health check
- Volume persistence

#### 2. SB-Scraper
- FastAPI uygulaması
- SeleniumBase ile Chrome
- Health check
- PostgreSQL'e bağımlı

#### 3. Log Viewer
- Flask uygulaması
- PostgreSQL'e bağımlı
- Health check
- Connection pool optimizasyonu
- Polling tabanlı canlı güncelleme

### Docker Komutları

```bash
# Servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down

# Servisleri durdur ve volume'ları sil
docker-compose down -v

# Logları görüntüle
docker-compose logs -f

# Belirli bir servisin loglarını görüntüle
docker-compose logs -f sb-scraper

# Servisi yeniden başlat
docker-compose restart sb-scraper

# Yeni build ile başlat
docker-compose up -d --build

# Servis durumunu kontrol et
docker-compose ps
```

### Dockerfile Yapısı

Dockerfile multi-stage build kullanır:

1. **Base Stage**: Temel kurulumlar (Chrome, fonts, dependencies)
2. **Python-Deps Stage**: Python bağımlılıkları
3. **Final Stage**: Uygulama kodu ve çalışma ortamı

Bu yapı, image boyutunu küçültür ve build sürelerini optimize eder.

---

## 📂 Proje Yapısı

```
sb-scrapper/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI ana uygulama
│   ├── config.py               # Konfigürasyon yönetimi
│   ├── schemas.py              # Pydantic modelleri
│   ├── swagger_config.py       # Swagger konfigürasyonu
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── browser.py          # SeleniumBase browser manager
│   │   ├── logger.py           # Loguru logger
│   │   ├── postgres_logger.py  # PostgreSQL log handler
│   │   └── blacklist.py        # Black-list yönetimi
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py       # PostgreSQL connection pool
│   │   └── models.py           # SQLAlchemy modelleri
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── request_tracker.py  # Request tracking middleware
│   │
│   ├── payloads/
│   │   ├── __init__.py
│   │   ├── noise_js.py         # Canvas noise JavaScript
│   │   └── sentinel_js.py      # JS sentinel (popup remover)
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── queue.py            # Async task queue
│   │
│   └── utils/
│       ├── __init__.py
│       ├── monitor.py          # System monitor
│       ├── memory_monitor.py   # Memory monitor
│       └── user_agents.py      # User agent listesi
│
├── log-viewer/
│   ├── app.py                  # Flask uygulaması
│   ├── db_pool.py              # Connection pool context manager
│   ├── Dockerfile              # Log viewer Dockerfile
│   ├── requirements.txt        # Python bağımlılıkları
│   ├── static/                 # Static dosyalar
│   │   ├── css/
│   │   ├── js/
│   │   └── favicon.ico
│   └── templates/
│       ├── index.html          # Ana dashboard
│       └── favicon.ico
│
├── migrations/
│   ├── 001_initial_schema.sql  # Tablolar
│   ├── 002_add_indexes.sql     # İndeksler
│   ├── 003_cleanup_function.sql # Cleanup fonksiyonu
│   ├── 004_jsonb_migration.sql # JSONB migrasyonu
│   ├── 005_partitioning.sql    # Partitioning
│   └── 006_retention_policy.sql # Retention policy
│
├── static/
│   └── swagger-ui.css          # Custom Swagger CSS
│
├── black-list.lst              # Yasaklı domain listesi
├── .env.example                # Örnek environment dosyası
├── .dockerignore               # Docker ignore dosyası
├── .gitignore                  # Git ignore dosyası
├── docker-compose.yml          # Docker Compose konfigürasyonu
├── Dockerfile                  # Ana Dockerfile
├── requirements.txt            # Python bağımlılıkları
└── LICENSE                     # MIT lisansı
```

---

## 🔒 Güvenlik

### API Key Authentication

API key doğrulamayı etkinleştirmek için:

```bash
# .env dosyasında
AUTH_ENABLED=true
AUTH_API_KEY=your_secret_api_key_here
```

Request gönderirken header ekleyin:

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_api_key_here" \
  -d '{"url": "https://example.com"}'
```

### Rate Limiting

Rate limiting'i etkinleştirmek için:

```bash
# .env dosyasında
RATE_LIMITING_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

### CORS

CORS'u etkinleştirmek için:

```bash
# .env dosyasında
CORS_ENABLED=true
CORS_ORIGINS=["https://example.com"]
CORS_METHODS=["GET","POST"]
CORS_HEADERS=["*"]
```

### Sensitive Header Filtering

Hassas header'lar otomatik olarak filtrelenir:

```python
SENSITIVE_HEADERS=authorization,cookie,x-api-key,token,x-auth-token
```

---

### Kod Standartları

- **PEP 8**: Python kod standartlarına uyun
- **Type Hints**: Fonksiyonlarda type hints kullanın
- **Docstrings**: Fonksiyon ve sınıflar için docstring ekleyin
- **Comments**: Karmaşık kodları açıklayın

---

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [`LICENSE`](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- **SeleniumBase**: Mükemmel scraping kütüphanesi için
- **FastAPI**: Modern ve hızlı web framework için
- **PostgreSQL**: Güçlü veritabanı için
- **Loguru**: Güzel logging kütüphanesi için

---

<div align="center">

**⭐ Eğer bu projeyi beğendiyseniz, lütfen yıldız vermeyi unutmayın!**

</div>
