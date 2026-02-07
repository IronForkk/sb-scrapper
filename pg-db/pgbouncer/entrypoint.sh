#!/bin/sh
set -e

echo "--- PgBouncer Entrypoint: Başlatılıyor ---"
echo "Mevcut Ortam Değişkenleri:"
printenv | sort
echo "-----------------------------------------"

# pgbouncer.ini dosyasını oluştur
echo "pgbouncer.ini.template dosyasından /etc/pgbouncer/pgbouncer.ini oluşturuluyor..."
envsubst < /config/pgbouncer/pgbouncer.ini.template > /etc/pgbouncer/pgbouncer.ini
echo "OLUŞTURULAN /etc/pgbouncer/pgbouncer.ini İÇERİĞİ:"
cat /etc/pgbouncer/pgbouncer.ini
echo "-----------------------------------------"

# userlist.txt dosyasını oluştur
echo "userlist.txt.template dosyasından /etc/pgbouncer/userlist.txt oluşturuluyor..."
envsubst < /config/pgbouncer/userlist.txt.template > /etc/pgbouncer/userlist.txt
echo "OLUŞTURULAN /etc/pgbouncer/userlist.txt İÇERİĞİ:"
cat /etc/pgbouncer/userlist.txt
echo "-----------------------------------------"

echo "PgBouncer başlatılıyor..."
# Dockerfile'da CMD olarak belirtilen asıl komutu çalıştır
exec "$@"

