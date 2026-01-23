"""
User Agent Listesi
Farklı tarayıcı ve işletim sistemleri için User Agent string'leri
"""
import random

# Windows User Agent'ları
WINDOWS_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# macOS User Agent'ları
MACOS_UA = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Linux User Agent'ları
LINUX_UA = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Tüm User Agent'lar
ALL_USER_AGENTS = WINDOWS_UA + MACOS_UA + LINUX_UA


def get_random_user_agent(platform: str = None) -> str:
    """
    Rastgele bir User Agent döndürür.
    
    Args:
        platform: 'windows', 'macos', 'linux' veya None (hepsi)
    
    Returns:
        User Agent string'i
    """
    if platform == 'windows':
        return random.choice(WINDOWS_UA)
    elif platform == 'macos':
        return random.choice(MACOS_UA)
    elif platform == 'linux':
        return random.choice(LINUX_UA)
    else:
        return random.choice(ALL_USER_AGENTS)
