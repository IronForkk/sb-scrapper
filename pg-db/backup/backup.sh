#!/bin/sh

# Hata durumunda script'in durmasını sağlar
set -e

export PGPASSWORD

echo "Yedekleme döngüsü başlatıldı. Ayarlar:"
echo "Veritabanı: ${POSTGRES_DB}"
echo "Kullanıcı: ${POSTGRES_USER}"
echo "Yedekleme Aralığı: ${BACKUP_INTERVAL} saniye"
echo "Yedek Saklama Süresi: ${BACKUP_RETENTION_DAYS} gün"
echo "-------------------------------------------------"

while true; do
  echo "$(date +'%Y-%m-%d %H:%M:%S') - Yedekleme başlıyor..."
  
  # Yedekleme işlemini yap ve gzip ile sıkıştır
  # --if-exists seçeneği drop edilecek nesne yoksa hata vermesini engeller
  pg_dump --clean --if-exists -h postgres -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip > "/backups/backup_$(date +%Y-%m-%dT%H-%M-%S).sql.gz"
  
  echo "$(date +'%Y-%m-%d %H:%M:%S') - Yedekleme tamamlandı."
  
  echo "$(date +'%Y-%m-%d %H:%M:%S') - Belirtilen günden eski yedekler temizleniyor..."
  
  # find komutu ile eski yedekleri bul ve sil
  find /backups -type f -mtime "+${BACKUP_RETENTION_DAYS}" -name '*.sql.gz' -delete
  
  echo "$(date +'%Y-%m-%d %H:%M:%S') - Temizlik tamamlandı. ${BACKUP_INTERVAL} saniye bekleniyor..."
  
  sleep "${BACKUP_INTERVAL}"
done