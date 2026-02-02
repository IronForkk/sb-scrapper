-- PostgreSQL JSONB Migration
-- SB-Scrapper loglama altyapısı için TEXT alanları JSONB tipine çevirir

-- application_logs tablosu için
ALTER TABLE application_logs
ALTER COLUMN extra_data TYPE JSONB USING extra_data::jsonb;

-- request_logs tablosu için
ALTER TABLE request_logs
ALTER COLUMN headers TYPE JSONB USING headers::jsonb;
ALTER TABLE request_logs
ALTER COLUMN query_params TYPE JSONB USING query_params::jsonb;
ALTER TABLE request_logs
ALTER COLUMN body TYPE JSONB USING body::jsonb;
ALTER TABLE request_logs
ALTER COLUMN body_error TYPE JSONB USING body_error::jsonb;

-- error_logs tablosu için
ALTER TABLE error_logs
ALTER COLUMN extra_data TYPE JSONB USING extra_data::jsonb;

-- JSONB alanları için GIN indeksleri (performans optimizasyonu)
CREATE INDEX IF NOT EXISTS idx_application_logs_extra_data_gin ON application_logs USING GIN (extra_data);
CREATE INDEX IF NOT EXISTS idx_request_logs_headers_gin ON request_logs USING GIN (headers);
CREATE INDEX IF NOT EXISTS idx_request_logs_query_params_gin ON request_logs USING GIN (query_params);
CREATE INDEX IF NOT EXISTS idx_request_logs_body_gin ON request_logs USING GIN (body);
CREATE INDEX IF NOT EXISTS idx_error_logs_extra_data_gin ON error_logs USING GIN (extra_data);
