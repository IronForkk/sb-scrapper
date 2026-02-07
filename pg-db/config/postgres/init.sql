-- PostgreSQL Initial Schema
-- SB-Scrapper loglama altyapısı için tablolar
-- Tek init.sql dosyası - migration sistemi yok

-- Application Logs Tablosu
CREATE TABLE IF NOT EXISTS application_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    module VARCHAR(255),
    function_name VARCHAR(255),
    line_number INTEGER,
    message TEXT NOT NULL,
    extra_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Request Logs Tablosu
-- Request ve Response bilgilerini loglar (Response body loglanmaz - güvenlik)
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ip VARCHAR(45) NOT NULL,
    port INTEGER,
    method VARCHAR(10) NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')),
    path TEXT NOT NULL,
    full_url TEXT,
    headers TEXT,
    query_params TEXT,
    user_agent TEXT,
    body TEXT,
    body_error TEXT,
    response_status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Domain Stats Tablosu (Scraping istatistikleri için)
CREATE TABLE IF NOT EXISTS domain_stats (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    domain VARCHAR(255) NOT NULL,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2),
    -- Ekran Görüntüleri
    raw_desktop_ss_count INTEGER DEFAULT 0,
    raw_mobile_ss_count INTEGER DEFAULT 0,
    main_desktop_ss_count INTEGER DEFAULT 0,
    google_ss_count INTEGER DEFAULT 0,
    ddg_ss_count INTEGER DEFAULT 0,
    -- HTML Kaynak Kodları
    raw_html_count INTEGER DEFAULT 0,
    google_html_count INTEGER DEFAULT 0,
    ddg_html_count INTEGER DEFAULT 0,
    -- Diğer İstatistikler
    network_logs_count INTEGER DEFAULT 0,
    total_duration DECIMAL(10,2) DEFAULT 0,
    avg_duration DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Error Logs Tablosu (Ayrı tablo - hızlı sorgulama için)
CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL CHECK (level IN ('ERROR', 'CRITICAL')),
    module VARCHAR(255),
    function_name VARCHAR(255),
    line_number INTEGER,
    message TEXT NOT NULL,
    stack_trace TEXT,
    url TEXT,
    domain VARCHAR(255),
    extra_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Gunicorn Logs Tablosu (Gunicorn logları için)
CREATE TABLE IF NOT EXISTS gunicorn_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    worker_id VARCHAR(50),
    message TEXT NOT NULL,
    extra_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEKSLER
-- ============================================

-- Application Logs Indeksleri
CREATE INDEX IF NOT EXISTS idx_app_logs_timestamp ON application_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_app_logs_level ON application_logs(level);
CREATE INDEX IF NOT EXISTS idx_app_logs_module ON application_logs(module);
-- Composite index: timestamp + level (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_app_logs_timestamp_level ON application_logs(timestamp DESC, level);

-- Request Logs Indeksleri
CREATE INDEX IF NOT EXISTS idx_req_logs_timestamp ON request_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_req_logs_ip ON request_logs(ip);
CREATE INDEX IF NOT EXISTS idx_req_logs_path ON request_logs(path);
CREATE INDEX IF NOT EXISTS idx_req_logs_method ON request_logs(method);
CREATE INDEX IF NOT EXISTS idx_req_logs_status_code ON request_logs(response_status_code);
-- Composite index: timestamp + status_code (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_req_logs_timestamp_status ON request_logs(timestamp DESC, response_status_code);
-- Composite index: path + timestamp (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_req_logs_path_timestamp ON request_logs(path, timestamp DESC);

-- Error Logs Indeksleri
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_level ON error_logs(level);
CREATE INDEX IF NOT EXISTS idx_error_logs_domain ON error_logs(domain);
-- Composite index: timestamp + domain (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp_domain ON error_logs(timestamp DESC, domain);

-- Domain Stats Indeksleri
CREATE INDEX IF NOT EXISTS idx_domain_stats_timestamp ON domain_stats(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_domain_stats_domain ON domain_stats(domain);
-- Composite index: domain + timestamp (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_domain_stats_domain_timestamp ON domain_stats(domain, timestamp DESC);

-- Gunicorn Logs Indeksleri
CREATE INDEX IF NOT EXISTS idx_gunicorn_logs_timestamp ON gunicorn_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gunicorn_logs_level ON gunicorn_logs(level);
CREATE INDEX IF NOT EXISTS idx_gunicorn_logs_worker_id ON gunicorn_logs(worker_id);
-- Composite index: timestamp + level (sık kullanılan filtreler için)
CREATE INDEX IF NOT EXISTS idx_gunicorn_logs_timestamp_level ON gunicorn_logs(timestamp DESC, level);
