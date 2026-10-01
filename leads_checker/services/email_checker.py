"""Сервис проверки email через Abstract API Email Reputation"""
import aiohttp
import asyncio
from config import ABSTRACT_API_KEY, ABSTRACT_API_URL


class EmailChecker:
    """Проверка email адресов через Email Reputation API"""
    
    def __init__(self):
        self.api_key = ABSTRACT_API_KEY
        self.base_url = ABSTRACT_API_URL
    
    async def check(self, email: str) -> dict:
        """
        Проверяет email адрес через Email Reputation API
        
        Args:
            email: Email адрес для проверки
            
        Returns:
            dict: Результаты проверки
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        url = f"{self.base_url}?api_key={self.api_key}&email={email}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Извлекаем данные из новой структуры ответа
                        deliverability = data.get("email_deliverability", {})
                        quality = data.get("email_quality", {})
                        risk = data.get("email_risk", {})
                        breaches = data.get("email_breaches", {})
                        
                        return {
                            # Deliverability
                            "deliverability": deliverability.get("status", "unknown").upper(),
                            "deliverability_detail": deliverability.get("status_detail", ""),
                            "valid_format": deliverability.get("is_format_valid", False),
                            "is_smtp_valid": deliverability.get("is_smtp_valid", False),
                            "is_mx_valid": deliverability.get("is_mx_valid", False),
                            "mx_records": deliverability.get("mx_records", []),
                            
                            # Quality
                            "quality_score": quality.get("score") if quality.get("score") is not None else 0.0,
                            "free": quality.get("is_free_email", False),
                            "disposable": quality.get("is_disposable", False),
                            "is_catchall_email": quality.get("is_catchall", False),
                            "is_role_email": quality.get("is_role", False),
                            "is_username_suspicious": quality.get("is_username_suspicious", False),
                            "is_subaddress": quality.get("is_subaddress", False),
                            "is_dmarc_enforced": quality.get("is_dmarc_enforced", False),
                            "is_spf_strict": quality.get("is_spf_strict", False),
                            "minimum_age": quality.get("minimum_age"),
                            
                            # Risk
                            "address_risk_status": risk.get("address_risk_status", "unknown"),
                            "domain_risk_status": risk.get("domain_risk_status", "unknown"),
                            
                            # Breaches
                            "total_breaches": breaches.get("total_breaches", 0),
                            "date_first_breached": breaches.get("date_first_breached"),
                            "date_last_breached": breaches.get("date_last_breached"),
                            
                            # Domain info
                            "domain": data.get("email_domain", {}).get("domain", ""),
                            "domain_age": data.get("email_domain", {}).get("domain_age"),
                            "is_risky_tld": data.get("email_domain", {}).get("is_risky_tld", False),
                            
                            "error": None
                        }
                    elif response.status == 422:
                        # Quota reached - возвращаем специальную ошибку
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", {}).get("message", "Quota reached")
                            return {"error": f"Quota reached: {error_msg}"}
                        except:
                            return {"error": "Quota reached"}
                    elif response.status == 429:
                        # Too many requests - возвращаем специальную ошибку
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", {}).get("message", "Too many requests")
                            return {"error": f"Rate limit: {error_msg}"}
                        except:
                            return {"error": "Rate limit exceeded"}
                    else:
                        error_text = await response.text()
                        return {"error": f"API returned status {response.status}: {error_text}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
