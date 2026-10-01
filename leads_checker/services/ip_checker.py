"""Сервис проверки IP через ipdata.co"""
import aiohttp
import asyncio
from config import IPDATA_API_KEY, IPDATA_API_URL


class IPChecker:
    """Проверка IP адресов"""
    
    def __init__(self):
        self.api_key = IPDATA_API_KEY
        self.base_url = IPDATA_API_URL
    
    async def check(self, ip: str) -> dict:
        """
        Проверяет IP адрес
        
        Args:
            ip: IP адрес для проверки
            
        Returns:
            dict: Результаты проверки
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        # Проверяем, не является ли IP приватным/локальным
        parts = ip.split('.')
        if len(parts) == 4:
            try:
                first_octet = int(parts[0])
                second_octet = int(parts[1])
                # Приватные IP диапазоны
                if (first_octet == 10 or
                    (first_octet == 172 and 16 <= second_octet <= 31) or
                    (first_octet == 192 and second_octet == 168) or
                    first_octet == 127 or  # localhost
                    (first_octet == 169 and second_octet == 254)):  # link-local
                    return {
                        "error": "Private/local IP address (cannot be checked via public API)",
                        "is_private": True,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_anonymous": False,
                        "is_known_attacker": False,
                        "is_known_abuser": False,
                        "is_threat": False,
                        "is_bogon": True
                    }
            except (ValueError, IndexError):
                pass
        
        url = f"{self.base_url}{ip}?api-key={self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "is_tor": data.get("threat", {}).get("is_tor", False),
                            "is_proxy": data.get("threat", {}).get("is_proxy", False),
                            "is_anonymous": data.get("threat", {}).get("is_anonymous", False),
                            "is_known_attacker": data.get("threat", {}).get("is_known_attacker", False),
                            "is_known_abuser": data.get("threat", {}).get("is_known_abuser", False),
                            "is_threat": data.get("threat", {}).get("is_threat", False),
                            "is_bogon": data.get("threat", {}).get("is_bogon", False),
                            "country_code": data.get("country_code", ""),
                            "country_name": data.get("country_name", ""),
                            "city": data.get("city", ""),
                            "asn": str(data.get("asn", "")) if data.get("asn") else "",
                            "asn_name": data.get("asn", {}).get("name", "") if isinstance(data.get("asn"), dict) else "",
                            "error": None
                        }
                    else:
                        return {"error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
