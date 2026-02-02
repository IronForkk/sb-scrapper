-- PostgreSQL Indexes
-- Performans için indeksler (Composite index'ler dahil)

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
