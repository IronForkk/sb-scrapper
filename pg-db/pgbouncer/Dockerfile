# Dockerfile to build pgbouncer from source

# ==========================================================================
# AŞAMA 1: DERLEME ORTAMI
# Bu aşamada, PgBouncer'ı kaynak kodundan derlemek için gerekli olan
# tüm araçları (gcc, make vb.) içeren bir ortam oluşturulur.
# ==========================================================================
FROM alpine:3.21 AS build
ARG VERSION=1.24.1

# Gerekli derleme bağımlılıklarını yükle
RUN apk add --no-cache autoconf automake curl gcc git libc-dev libevent-dev libtool make openssl-dev pkgconfig

# PgBouncer kaynak kodunu indir ve aç
RUN curl -sS -o /pgbouncer.tar.gz -L https://pgbouncer.github.io/downloads/files/$VERSION/pgbouncer-$VERSION.tar.gz && \
    tar -xzf /pgbouncer.tar.gz && mv /pgbouncer-$VERSION /pgbouncer

# Kaynak kodunu derle
RUN cd /pgbouncer && ./configure --prefix=/usr && make


# ==========================================================================
# AŞAMA 2: NİHAİ İMAJ
# Bu aşama, derlenmiş PgBouncer'ı ve sadece çalışması için gereken
# minimum bağımlılıkları içeren küçük ve güvenli bir imaj oluşturur.
# ==========================================================================
FROM alpine:3.21

# DÜZELTME: 'envsubst' komutunu kullanabilmek için 'gettext' paketi eklendi.
# Sadece gerekli olan paketleri yükle
RUN apk add --no-cache gettext libevent postgresql-client && \
    mkdir -p /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer && \
    touch /etc/pgbouncer/userlist.txt && \
    # Gerekli dizinlerin sahipliğini postgres kullanıcısına ver
    # 'postgresql-client' paketi 'postgres' kullanıcısını zaten oluşturduğu için tekrar eklemiyoruz.
    chown -R postgres /var/log/pgbouncer /var/run/pgbouncer /etc/pgbouncer

# Gerekli script ve dosyaları kopyala
COPY entrypoint.sh /entrypoint.sh
# YENİ EKLENEN SATIR: Başlatma scriptini çalıştırılabilir yap.
RUN chmod +x /entrypoint.sh
COPY --from=build /pgbouncer/pgbouncer /usr/bin

# Konteyner portunu dışarı aç
EXPOSE 6432
# Konteyneri 'postgres' kullanıcısı ile çalıştır
USER postgres
# Konteyner başladığında çalışacak olan script
ENTRYPOINT ["/entrypoint.sh"]
# Varsayılan olarak çalıştırılacak komut
CMD ["/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]

