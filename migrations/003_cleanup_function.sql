-- Retention Policy Function
-- Eski logları temizlemek için cron job veya scheduled task ile kullanılabilir

CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS void AS $$
BEGIN
    -- Application logs (30 gün varsayılan, parametre ile değiştirilebilir)
    DELETE FROM application_logs
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Error logs (30 gün varsayılan)
    DELETE FROM error_logs
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Request logs (30 gün varsayılan)
    DELETE FROM request_logs
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Domain stats (30 gün varsayılan)
    DELETE FROM domain_stats
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    RAISE NOTICE 'Eski loglar temizlendi: %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Fonksiyonu manuel olarak test etmek için:
-- SELECT cleanup_old_logs();
