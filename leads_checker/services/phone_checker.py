"""Сервис проверки телефона через numverify"""
import aiohttp
import asyncio
from config import NUMVERIFY_API_KEY, NUMVERIFY_API_URL


class PhoneChecker:
    """Проверка телефонных номеров"""
    
    def __init__(self):
        self.api_key = NUMVERIFY_API_KEY
        self.base_url = NUMVERIFY_API_URL
    
    async def check(self, phone: str) -> dict:
        """
        Проверяет телефонный номер
        
        Args:
            phone: Телефонный номер для проверки
            
        Returns:
            dict: Результаты проверки
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        # Убираем пробелы и форматируем номер
        # Сначала убираем все пробелы, затем другие символы
        phone_clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
        
        # Базовая валидация формата - номер должен быть достаточно длинным
        # Минимум 7 цифр для валидного номера (без кода страны)
        # Оставляем + если есть (для международного формата)
        digits_only = ''.join(filter(str.isdigit, phone_clean))
        if len(digits_only) < 7:
            return {
                "valid": False,
                "number": phone_clean,
                "error": "Phone number too short (minimum 7 digits required)",
                "line_type": "",
                "carrier": ""
            }
        
        url = f"{self.base_url}?access_key={self.api_key}&number={phone_clean}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "valid": data.get("valid", False),
                            "number": data.get("number", ""),
                            "local_format": data.get("local_format", ""),
                            "international_format": data.get("international_format", ""),
                            "country_prefix": data.get("country_prefix", ""),
                            "country_code": data.get("country_code", ""),
                            "country_name": data.get("country_name", ""),
                            "location": data.get("location") or "",
                            "carrier": data.get("carrier") or "",
                            "line_type": data.get("line_type") or "",
                            "error": None
                        }
                    else:
                        return {"error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
