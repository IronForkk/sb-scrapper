-- PostgreSQL Retention Policy Migration
-- SB-Scrapper log tabloları için otomatik temizleme fonksiyonları

-- Log retention ayarı için configuration tablosu
CREATE TABLE IF NOT EXISTS log_retention_config (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL UNIQUE,
    retention_days INTEGER NOT NULL DEFAULT 30,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Varsayılan retention ayarlarını ekle
INSERT INTO log_retention_config (table_name, retention_days, enabled) VALUES
    ('application_logs', 30, true),
    ('error_logs', 90, true),
    ('request_logs', 30, true),
    ('domain_stats', 365, true)
ON CONFLICT (table_name) DO NOTHING;

-- Cleanup fonksiyonunu güncelle (config tablosunu kullanır)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS TABLE(
    table_name VARCHAR,
    deleted_count BIGINT,
    status VARCHAR
) AS $$
DECLARE
    config_record RECORD;
    deleted_count_val BIGINT;
BEGIN
    -- Her tablo için cleanup yap
    FOR config_record IN
        SELECT table_name, retention_days, enabled
        FROM log_retention_config
        WHERE enabled = true
    LOOP
        BEGIN
            -- application_logs için
            IF config_record.table_name = 'application_logs' THEN
                EXECUTE format('
                    DELETE FROM %I
                    WHERE created_at < NOW() - INTERVAL %L
                ', config_record.table_name, (config_record.retention_days || ' days'));

                GET DIAGNOSTICS deleted_count_val = ROW_COUNT;
                RETURN QUERY SELECT config_record.table_name, deleted_count_val, 'success'::VARCHAR;

            -- error_logs için
            ELSIF config_record.table_name = 'error_logs' THEN
                EXECUTE format('
                    DELETE FROM %I
                    WHERE created_at < NOW() - INTERVAL %L
                ', config_record.table_name, (config_record.retention_days || ' days'));

                GET DIAGNOSTICS deleted_count_val = ROW_COUNT;
                RETURN QUERY SELECT config_record.table_name, deleted_count_val, 'success'::VARCHAR;

            -- request_logs için
            ELSIF config_record.table_name = 'request_logs' THEN
                EXECUTE format('
                    DELETE FROM %I
                    WHERE created_at < NOW() - INTERVAL %L
                ', config_record.table_name, (config_record.retention_days || ' days'));

                GET DIAGNOSTICS deleted_count_val = ROW_COUNT;
                RETURN QUERY SELECT config_record.table_name, deleted_count_val, 'success'::VARCHAR;

            -- domain_stats için
            ELSIF config_record.table_name = 'domain_stats' THEN
                EXECUTE format('
                    DELETE FROM %I
                    WHERE created_at < NOW() - INTERVAL %L
                ', config_record.table_name, (config_record.retention_days || ' days'));

                GET DIAGNOSTICS deleted_count_val = ROW_COUNT;
                RETURN QUERY SELECT config_record.table_name, deleted_count_val, 'success'::VARCHAR;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            RETURN QUERY SELECT config_record.table_name, 0::BIGINT, 'error: ' || SQLERRM::VARCHAR;
        END;
    END LOOP;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Tek tablo için cleanup fonksiyonu
CREATE OR REPLACE FUNCTION cleanup_table_logs(table_name VARCHAR, retention_days INTEGER DEFAULT NULL)
RETURNS BIGINT AS $$
DECLARE
    actual_retention_days INTEGER;
    deleted_count BIGINT;
BEGIN
    -- Retention days belirtilmemişse config'den al
    IF retention_days IS NULL THEN
        SELECT retention_days INTO actual_retention_days
        FROM log_retention_config
        WHERE table_name = cleanup_table_logs.table_name
        LIMIT 1;

        IF actual_retention_days IS NULL THEN
            actual_retention_days := 30; -- Varsayılan değer
        END IF;
    ELSE
        actual_retention_days := retention_days;
    END IF;

    -- Delete işlemi
    EXECUTE format('
        DELETE FROM %I
        WHERE created_at < NOW() - INTERVAL %L
    ', table_name, (actual_retention_days || ' days'));

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Retention ayarını güncelleme fonksiyonu
CREATE OR REPLACE FUNCTION update_retention_days(table_name VARCHAR, retention_days INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE log_retention_config
    SET retention_days = update_retention_days.retention_days,
        updated_at = NOW()
    WHERE table_name = update_retention_days.table_name;

    IF FOUND THEN
        RETURN true;
    ELSE
        -- Yeni kayıt ekle
        INSERT INTO log_retention_config (table_name, retention_days, enabled)
        VALUES (update_retention_days.table_name, update_retention_days.retention_days, true);
        RETURN true;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Log cleanup için trigger fonksiyonu (yeni partition oluştururken otomatik cleanup)
CREATE OR REPLACE FUNCTION on_new_partition_cleanup()
RETURNS TRIGGER AS $$
BEGIN
    -- Yeni partition oluşturulduğunda eski partition'ları temizle
    PERFORM drop_old_partitions('application_logs', 12);
    PERFORM drop_old_partitions('error_logs', 12);
    PERFORM drop_old_partitions('request_logs', 12);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- VACUUM ANALYZE fonksiyonu (performans için)
CREATE OR REPLACE FUNCTION vacuum_analyze_tables()
RETURNS TABLE(table_name VARCHAR, status VARCHAR) AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND (tablename LIKE '%_logs' OR tablename = 'domain_stats')
    LOOP
        BEGIN
            EXECUTE format('VACUUM ANALYZE %I', table_record.tablename);
            RETURN QUERY SELECT table_record.tablename, 'success'::VARCHAR;
        EXCEPTION WHEN OTHERS THEN
            RETURN QUERY SELECT table_record.tablename, 'error: ' || SQLERRM::VARCHAR;
        END;
    END LOOP;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Log retention raporu fonksiyonu
CREATE OR REPLACE FUNCTION get_retention_report()
RETURNS TABLE(
    table_name VARCHAR,
    total_records BIGINT,
    table_size VARCHAR,
    retention_days INTEGER,
    oldest_record TIMESTAMP WITH TIME ZONE,
    records_to_delete BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lrc.table_name,
        COALESCE(
            (SELECT COUNT(*)::BIGINT FROM (
                SELECT 1 FROM application_logs WHERE table_name = 'application_logs' UNION ALL
                SELECT 1 FROM error_logs WHERE table_name = 'error_logs' UNION ALL
                SELECT 1 FROM request_logs WHERE table_name = 'request_logs' UNION ALL
                SELECT 1 FROM domain_stats WHERE table_name = 'domain_stats'
            ) AS subq),
            0
        ) as total_records,
        COALESCE(
            pg_size_pretty(pg_total_relation_size(lrc.table_name::regclass)),
            'N/A'
        ) as table_size,
        lrc.retention_days,
        COALESCE(
            (SELECT MIN(created_at) FROM (
                SELECT created_at FROM application_logs WHERE table_name = 'application_logs' UNION ALL
                SELECT created_at FROM error_logs WHERE table_name = 'error_logs' UNION ALL
                SELECT created_at FROM request_logs WHERE table_name = 'request_logs' UNION ALL
                SELECT created_at FROM domain_stats WHERE table_name = 'domain_stats'
            ) AS subq),
            NULL
        ) as oldest_record,
        COALESCE(
            (SELECT COUNT(*)::BIGINT FROM (
                SELECT 1 FROM application_logs WHERE table_name = 'application_logs' AND created_at < NOW() - (lrc.retention_days || ' days')::interval UNION ALL
                SELECT 1 FROM error_logs WHERE table_name = 'error_logs' AND created_at < NOW() - (lrc.retention_days || ' days')::interval UNION ALL
                SELECT 1 FROM request_logs WHERE table_name = 'request_logs' AND created_at < NOW() - (lrc.retention_days || ' days')::interval UNION ALL
                SELECT 1 FROM domain_stats WHERE table_name = 'domain_stats' AND created_at < NOW() - (lrc.retention_days || ' days')::interval
            ) AS subq),
            0
        ) as records_to_delete
    FROM log_retention_config lrc;
END;
$$ LANGUAGE plpgsql;
