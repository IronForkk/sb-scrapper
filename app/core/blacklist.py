"""
Black-List Yönetimi
Domain'leri filtrelemek için kullanılır
"""
from urllib.parse import urlparse


class BlacklistManager:
    """
    Black-list dosyasını yönetir ve domain kontrolü yapar
    """

    def __init__(self, file_path: str):
        """
        Black-list dosyasını yükler

        Args:
            file_path: Black-list dosya yolu
        """
        self.blacklist = set()
        self._load_blacklist(file_path)

    def _load_blacklist(self, file_path: str) -> None:
        """
        Dosyadan black-list domainlerini yükler

        Args:
            file_path: Black-list dosya yolu

        Raises:
            FileNotFoundError: Dosya bulunamazsa
            IOError: Dosya okunamazsa
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Boş satırları ve whitespace'i temizle
                    domain = line.strip()
                    if domain and not domain.startswith('#'):
                        self.blacklist.add(domain.lower())
        except FileNotFoundError:
            raise FileNotFoundError(f"Black-list dosyası bulunamadı: {file_path}")
        except IOError as e:
            raise IOError(f"Black-list dosyası okunamadı: {e}")

    def _extract_domain(self, url_or_domain: str) -> str:
        """
        URL veya domain'den domain kısmını çıkarır

        Args:
            url_or_domain: URL veya domain string'i

        Returns:
            Domain (küçük harf)
        """
        # Eğer http:// veya https:// ile başlıyorsa URL'dir
        if url_or_domain.startswith('http://') or url_or_domain.startswith('https://'):
            parsed = urlparse(url_or_domain)
            domain = parsed.netloc
        else:
            # URL değilse, domain olarak kabul et
            domain = url_or_domain

        # Port numarasını temizle
        if ':' in domain:
            domain = domain.split(':')[0]

        return domain.lower()

    def is_blacklisted(self, url_or_domain: str) -> bool:
        """
        Domain'in black-list'te olup olmadığını kontrol eder
        Subdomain kontrolü de yapar (Hata #3 düzeltmesi)

        Args:
            url_or_domain: Kontrol edilecek URL veya domain

        Returns:
            True if blacklisted, False otherwise
        """
        domain = self._extract_domain(url_or_domain)
        
        # Tam eşleşme kontrolü
        if domain in self.blacklist:
            return True
        
        # Subdomain kontrolü - parent domain'leri kontrol et
        parts = domain.split('.')
        for i in range(1, len(parts)):  # İlk parçadan başla (subdomain'i atla)
            parent_domain = '.'.join(parts[i:])
            if parent_domain in self.blacklist:
                return True
        
        return False

    def get_blacklist_count(self) -> int:
        """
        Black-list'teki domain sayısını döndürür

        Returns:
            Domain sayısı
        """
        return len(self.blacklist)
