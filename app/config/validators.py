"""
Konfigürasyon Validatörleri
"""
from typing import List


def parse_comma_separated_list(v: str | list[str]) -> list[str]:
    """
    JSON formatındaki string veya virgülle ayrılmış string'i listeye dönüştürür.
    Eğer zaten bir listeyse olduğu gibi döndürür.
    """
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # JSON formatı kontrol et (["item1","item2"])
        if v.startswith('[') and v.endswith(']'):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        # Virgülle ayrılmış string
        return [item.strip() for item in v.split(',') if item.strip()]
    return []
