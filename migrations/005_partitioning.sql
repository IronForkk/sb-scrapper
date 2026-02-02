-- PostgreSQL Partitioning Migration
-- SB-Scrapper log tabloları için partitioning yapısı

-- Önce mevcut tabloları partitioned tablolara dönüştür
-- Not: Bu işlem büyük veri setlerinde zaman alabilir

-- application_logs için partitioning
-- Önce primary key'i kaldır (partitioned tablolar için gereklidir)
ALTER TABLE application_logs DROP CONSTRAINT IF EXISTS application_logs_pkey;

-- Tabloyu partitioned yap
ALTER TABLE application_logs PARTITION BY RANGE (timestamp);

-- Primary key'i yeniden oluştur (partitioned tablo için)
ALTER TABLE application_logs ADD PRIMARY KEY (id, timestamp);

-- Mevcut veriler için partition oluştur (2025-01)
-- Not: Bu partition mevcut verileri içerecek şekilde ayarlanmıştır
CREATE TABLE IF NOT EXISTS application_logs_2025_01 PARTITION OF application_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Gelecek aylar için partition'lar oluştur
CREATE TABLE IF NOT EXISTS application_logs_2025_02 PARTITION OF application_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_03 PARTITION OF application_logs
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_04 PARTITION OF application_logs
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_05 PARTITION OF application_logs
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_06 PARTITION OF application_logs
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_07 PARTITION OF application_logs
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_08 PARTITION OF application_logs
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_09 PARTITION OF application_logs
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_10 PARTITION OF application_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_11 PARTITION OF application_logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS application_logs_2025_12 PARTITION OF application_logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Default partition (belirsiz tarihler için)
CREATE TABLE IF NOT EXISTS application_logs_default PARTITION OF application_logs
    DEFAULT;

-- error_logs için partitioning
ALTER TABLE error_logs DROP CONSTRAINT IF EXISTS error_logs_pkey;
ALTER TABLE error_logs PARTITION BY RANGE (timestamp);
ALTER TABLE error_logs ADD PRIMARY KEY (id, timestamp);

CREATE TABLE IF NOT EXISTS error_logs_2025_01 PARTITION OF error_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_02 PARTITION OF error_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_03 PARTITION OF error_logs
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_04 PARTITION OF error_logs
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_05 PARTITION OF error_logs
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_06 PARTITION OF error_logs
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_07 PARTITION OF error_logs
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_08 PARTITION OF error_logs
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_09 PARTITION OF error_logs
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_10 PARTITION OF error_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_11 PARTITION OF error_logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS error_logs_2025_12 PARTITION OF error_logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS error_logs_default PARTITION OF error_logs
    DEFAULT;

-- request_logs için partitioning
ALTER TABLE request_logs DROP CONSTRAINT IF EXISTS request_logs_pkey;
ALTER TABLE request_logs PARTITION BY RANGE (timestamp);
ALTER TABLE request_logs ADD PRIMARY KEY (id, timestamp);

CREATE TABLE IF NOT EXISTS request_logs_2025_01 PARTITION OF request_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_02 PARTITION OF request_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_03 PARTITION OF request_logs
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_04 PARTITION OF request_logs
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_05 PARTITION OF request_logs
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_06 PARTITION OF request_logs
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_07 PARTITION OF request_logs
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_08 PARTITION OF request_logs
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_09 PARTITION OF request_logs
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_10 PARTITION OF request_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_11 PARTITION OF request_logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS request_logs_2025_12 PARTITION OF request_logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS request_logs_default PARTITION OF request_logs
    DEFAULT;

-- Otomatik partition oluşturma fonksiyonu
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date DEFAULT NULL)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
    p_start_date date;
BEGIN
    -- Tarih belirtilmezse gelecek ay için oluştur
    IF start_date IS NULL THEN
        p_start_date := date_trunc('month', current_date + interval '1 month');
    ELSE
        p_start_date := start_date;
    END IF;

    end_date := p_start_date + interval '1 month';
    partition_name := table_name || '_' || to_char(p_start_date, 'YYYY_MM');

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
        FOR VALUES FROM (%L) TO (%L)
    ', partition_name, table_name, p_start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Partition cleanup fonksiyonu (eski partition'ları siler)
CREATE OR REPLACE FUNCTION drop_old_partitions(table_name text, keep_months integer DEFAULT 12)
RETURNS void AS $$
DECLARE
    partition_record RECORD;
    cutoff_date date;
BEGIN
    cutoff_date := date_trunc('month', current_date - interval '1 month' * keep_months);

    FOR partition_record IN
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE (table_name || '_%')
          AND tablename NOT LIKE '%default'
          AND tablename NOT LIKE '%_2025_%'  -- 2025 partition'larını koru
    LOOP
        -- Partition isminden tarih bilgisini çıkar
        BEGIN
            DECLARE
                partition_date date;
            BEGIN
                -- Partition isminden tarih bilgisini çıkar (format: table_YYYY_MM)
                partition_date := to_date(
                    substring(partition_record.tablename from length(table_name) + 2),
                    'YYYY_MM'
                );

                IF partition_date < cutoff_date THEN
                    EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', partition_record.tablename);
                    RAISE NOTICE 'Dropped partition: %', partition_record.tablename;
                END IF;
            END;
        EXCEPTION WHEN OTHERS THEN
            -- Tarih parse hatası varsa atla
            CONTINUE;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
