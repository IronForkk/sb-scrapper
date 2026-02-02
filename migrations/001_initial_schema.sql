-- PostgreSQL Initial Schema
-- SB-Scrapper loglama altyapısı için tablolar

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
-- Request ve Response bilgilerini loglar (Response body loglanmaz)
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
