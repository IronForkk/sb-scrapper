# SB-Scrapper

SeleniumBase tabanlı, anti-bot detection korumalı web scraping API'si. Intranet kullanımı için optimize edilmiş, tamamen senkron çalışan bir web scraping çözümüdür.

## 📋 İçindekiler

- [Özellikler](#özellikler)
- [Teknik Mimari](#teknik-mimari)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [API Dokümantasyonu](#api-dokümantasyonu)
- [Konfigürasyon](#konfigürasyon)
- [Proje Yapısı](#proje-yapısı)
- [Geliştirme Kuralları](#geliştirme-kuralları)
- [Lisans](#lisans)

## ✨ Özellikler

### Web Scraping
- **Çoklu Tarama Modu:** Ham URL ve ana domain taraması
- **Mobil Görünüm:** Mobil cihaz ekran görüntüleri (375x812)
- **Arama Motoru Entegrasyonu:** Google ve DuckDuckGo sonuçları
- **HTML Kaynak Kodu:** Sayfa kaynak kodlarını alma (Base64 formatında)

### Anti-Bot Detection
- **Canvas Noise:** Canvas fingerprinting bypass
- **JS Sentinel:** Popup ve engelleyici element temizleme
- **User Agent Rastgeleleştirme:** Windows, macOS, Linux platformları
- **WebDriver Tespit Önleme:** SeleniumBase ile gelişmiş gizlilik
- **Black-list Koruması:** İstenmeyen domain'leri filtreleme

### Loglama
- **PostgreSQL Loglama:** Tüm loglar veritabanında saklanır
- **Request Logging:** İstek detayları (headers, query params, body)
- **Error Logging:** Hatalar ayrı tabloda saklanır
- **Domain İstatistikleri:** Başarı/başarısız oranları takibi

## 🏗️ Teknik Mimari

### Temel Prensipler
- **Tamamen Senkron:** async/await, threading, multiprocessing YASAK
- **Tek İstek Modu:** Sıralı istek işleme, paralel istek YASAK
- **Merkezi Loglama:** Tüm loglar PostgreSQL'e
- **Intranet Uygulaması:** Rate limiting, authentication, CORS YASAK

### Teknoloji Yığını
- **Web Framework:** FastAPI
- **Browser Automation:** SeleniumBase
- **Veritabanı:** PostgreSQL (psycopg2 - senkron)
- **Loglama:** Loguru + PostgreSQL
- **Validasyon:** Pydantic
- **Konfigürasyon:** Pydantic Settings + python-dotenv

## 🚀 Kurulum

### Gereksinimler
- Python 3.11+
- Docker & Docker Compose (opsiyonel)
- PostgreSQL 15+

### Docker ile Kurulum (Önerilen)

1. **Depoyu klonlayın:**
```bash
git clone <repository-url>
cd sb-scrapper
```

2. **.env dosyasını oluşturun:**
```bash
cp .env.example .env
```

3. **.env dosyasını düzenleyin:**
```bash
# PostgreSQL şifresini belirleyin
POSTGRES_PASSWORD=güvenli_sifre_buraya
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

3. **PostgreSQL veritabanını başlatın:**
```bash
# init.sql dosyasını çalıştırın
psql -U postgres -d postgres -f db/init.sql
```

4. **.env dosyasını oluşturun ve düzenleyin:**
```bash
cp .env.example .env
```

5. **Uygulamayı başlatın:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## 📖 Kullanım

### API Endpoint

**POST /scrape**

Web sitesini tarar ve analiz eder.

### Örnek İstek

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "wait_time": 8,
    "process_raw_url": true,
    "process_main_domain": true,
    "get_html": true,
    "get_mobile_ss": true,
    "get_google_search": true,
    "get_google_html": true,
    "get_ddg_search": true,
    "get_ddg_html": true
  }'
```

### Örnek Yanıt

```json
{
  "success": true,
  "data": {
    "url": "https://example.com",
    "domain": "example.com",
    "screenshot_raw_url": "base64_encoded_image",
    "screenshot_mobile": "base64_encoded_image",
    "html_raw_url": "base64_encoded_html",
    "google_search_ss": "base64_encoded_image",
    "google_html": "base64_encoded_html",
    "ddg_search_ss": "base64_encoded_image",
    "ddg_html": "base64_encoded_html",
    "screenshot_main_domain": "base64_encoded_image",
    "html_main_domain": "base64_encoded_html",
    "logs": [
      {
        "timestamp": "2024-01-01T12:00:00Z",
        "level": "INFO",
        "message": "İşlem başladı"
      }
    ]
  },
  "execution_time": 15.5
}
```

### Python İstemci Örneği

```python
import requests

url = "http://localhost:8000/scrape"
payload = {
    "url": "https://example.com",
    "wait_time": 8,
    "process_raw_url": True,
    "process_main_domain": True,
    "get_html": True,
    "get_mobile_ss": True,
    "get_google_search": True,
    "get_google_html": True,
    "get_ddg_search": True,
    "get_ddg_html": True
}

response = requests.post(url, json=payload)
result = response.json()

if result["success"]:
    print(f"İşlem başarılı! Süre: {result['execution_time']} saniye")
else:
    print(f"Hata: {result['error']}")
```

## 📚 API Dokümantasyonu

### Swagger UI
Uygulama başlatıldığında otomatik olarak oluşturulur:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Health Check
```bash
curl http://localhost:8000/health
```

Yanıt:
```json
{
  "status": "healthy",
  "postgres_connected": true
}
```

## ⚙️ Konfigürasyon

### .env Dosyası

Tüm ayarlar `.env` dosyasından yönetilir. Örnek ayarlar:

#### Tarayıcı Ayarları
```env
HEADLESS=true                    # Headless mod
WAIT_TIME=8                      # Sayfa yükleme sonrası bekleme
USER_AGENT_PLATFORM=windows      # User Agent platform
PAGE_LOAD_TIMEOUT=60            # Sayfa yükleme zaman aşımı
BODY_CHECK_WAIT_TIME=2          # JS yüklenme bekleme süresi
PAGE_RELOAD_WAIT_TIME=5         # Sayfa yenileme bekleme süresi
```

#### API Ayarları
```env
HOST=0.0.0.0                    # Dinlenecek IP
PORT=8000                       # Dinlenecek port
```

#### Loglama Ayarları
```env
LOG_LEVEL=INFO                  # Log seviyesi
CONSOLE_LOGGING_ENABLED=true    # Konsol loglama
POSTGRES_LOGGING_ENABLED=true   # PostgreSQL loglama
STRUCTURED_LOGGING_ENABLED=false # JSON format loglama
```

#### Canvas Noise Ayarları
```env
NOISE_MIN_VALUE=-20             # Minimum noise değeri
NOISE_MAX_VALUE=20              # Maksimum noise değeri
```

#### Black-List Ayarları
```env
BLACKLIST_FILE=black-list.lst   # Black-list dosya yolu
```

#### PostgreSQL Ayarları
```env
POSTGRES_HOST=postgres          # PostgreSQL host
POSTGRES_PORT=5432              # PostgreSQL port
POSTGRES_DB=sb_scrapper         # Veritabanı adı
POSTGRES_USER=sb_user           # Kullanıcı adı
POSTGRES_PASSWORD=güvenli_sifre # Şifre
```

## 📁 Proje Yapısı

```
sb-scrapper/
├── app/
│   ├── main.py              # FastAPI ana uygulama (/scrape endpoint)
│   ├── config.py            # .env ayarları yönetimi
│   ├── schemas.py           # Pydantic request/response modelleri
│   ├── swagger_config.py    # Swagger dokümantasyonu
│   ├── core/
│   │   ├── browser.py       # SeleniumBase wrapper (senkron)
│   │   ├── logger.py        # Loguru logger
│   │   ├── postgres_logger.py  # PostgreSQL logger (senkron)
│   │   └── blacklist.py     # Black-list yönetimi
│   ├── payloads/
│   │   ├── noise_js.py      # Canvas noise JS (DOKUNMA!)
│   │   └── sentinel_js.py   # Sentinel JS (DOKUNMA!)
│   ├── db/
│   │   └── connection.py    # PostgreSQL bağlantısı (senkron)
│   └── utils/
│       └── user_agents.py   # User Agent listesi
├── db/
│   └── init.sql             # Veritabanı şeması
├── static/
│   └── swagger-ui.css       # Swagger UI CSS
├── black-list.lst           # Black-list domain listesi
├── .env                     # Ayarlar (oluşturulmalı)
├── .env.example             # Örnek ayarlar
├── docker-compose.yml       # Docker Compose konfigürasyonu
├── Dockerfile               # Docker imajı
├── requirements.txt         # Python bağımlılıkları
└── README.md                # Bu dosya
```

## 📜 Geliştirme Kuralları

### İzin Verilen Paketler
| Paket | Kullanım Alanı |
|-------|---------------|
| `fastapi` | Web framework (senkron mod) |
| `seleniumbase` | Browser automation |
| `loguru` | Logging |
| `psycopg2` | PostgreSQL (senkron) |
| `pydantic` | Validation |
| `pydantic-settings` | Config |
| `requests` | HTTP (senkron) |
| `httpx` | HTTP (senkron mod) |

## 🔒 Güvenlik

- **Black-list:** İstenmeyen domain'ler filtrelenir
- **Canvas Noise:** Fingerprinting tespiti zorlaştırılır
- **WebDriver Gizliliği:** SeleniumBase ile gelişmiş gizlilik
- **User Agent Rastgeleleştirme:** Her oturum için farklı UA
- **Response Body Loglama YOK:** Hassas veriler loglanmaz

## 📊 Veritabanı

### Tablolar

1. **application_logs:** Uygulama logları
2. **request_logs:** İstek logları (response body hariç)
3. **error_logs:** Hata logları
4. **domain_stats:** Domain istatistikleri

### Log Sorguları

```sql
-- Son 10 log
SELECT * FROM application_logs ORDER BY timestamp DESC LIMIT 10;

-- Hatalı istekler
SELECT * FROM error_logs ORDER BY timestamp DESC;

-- Domain istatistikleri
SELECT * FROM domain_stats ORDER BY timestamp DESC;
```

## 🐛 Hata Ayıklama

### Logları Görüntüleme

```bash
# Docker logları
docker-compose logs -f sb-scraper

# PostgreSQL logları
docker-compose logs -f postgres
```

### Veritabanına Bağlanma

```bash
docker exec -it sb-postgres psql -U sb_user -d sb_scrapper
```

### Test İsteği

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 📄 Lisans

Bu proje [LICENSE](LICENSE) dosyasında belirtilen lisans altında lisanslanmıştır.

**SB-Scrapper v3.0.0** - SeleniumBase tabanlı web scraping API'si
