"""Сервисы проверки социальных сетей через RapidAPI"""
import aiohttp
import asyncio
from config import (
    RAPIDAPI_KEY,
    FACEBOOK_API_HOST,
    GOOGLE_API_HOST,
    INSTAGRAM_API_HOST,
    SNAPCHAT_API_HOST,
    X_API_HOST
)


class FacebookChecker:
    """Проверка Facebook аккаунта по email"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = FACEBOOK_API_HOST
    
    async def check(self, email: str) -> dict:
        """Проверяет наличие Facebook аккаунта по email"""
        if not self.api_key:
            return {"exists": False, "error": "API key not configured"}
        
        url = f"https://{self.host}/check"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        payload = {"email": email}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_value = data.get("result", "")
                        exists = data.get("exists", False) or data.get("found", False) or (result_value and str(result_value).lower() == "true")
                        return {
                            "exists": bool(exists),
                            "error": None
                        }
                    else:
                        return {"exists": False, "error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"exists": False, "error": "Request timeout"}
        except Exception as e:
            return {"exists": False, "error": str(e)}


class GoogleChecker:
    """Проверка Google аккаунта (верификация Gmail)"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = GOOGLE_API_HOST
    
    async def check(self, email: str) -> dict:
        """Проверяет наличие Google аккаунта по email"""
        if not self.api_key:
            return {"exists": False, "error": "API key not configured"}
        
        # Проверяем, что это Gmail
        if not email or not str(email).lower().endswith("@gmail.com"):
            return {"exists": False, "error": "Not a Gmail address"}
        
        url = f"https://{self.host}/check"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        payload = {"email": email}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_value = data.get("result", "")
                        exists = data.get("exists", False) or data.get("valid", False) or (result_value and str(result_value).lower() == "true")
                        return {
                            "exists": bool(exists),
                            "error": None
                        }
                    else:
                        return {"exists": False, "error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"exists": False, "error": "Request timeout"}
        except Exception as e:
            return {"exists": False, "error": str(e)}


class InstagramChecker:
    """Проверка Instagram аккаунта"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = INSTAGRAM_API_HOST
    
    async def check(self, username_or_email: str) -> dict:
        """Проверяет наличие Instagram аккаунта"""
        if not self.api_key:
            return {"exists": False, "error": "API key not configured"}
        
        url = f"https://{self.host}/check"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        # Определяем, это email или username
        if "@" in username_or_email:
            payload = {"email": username_or_email}
        else:
            payload = {"username": username_or_email}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_value = data.get("result", "")
                        exists = data.get("exists", False) or data.get("found", False) or (result_value and str(result_value).lower() == "true")
                        return {
                            "exists": bool(exists),
                            "error": None
                        }
                    else:
                        return {"exists": False, "error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"exists": False, "error": "Request timeout"}
        except Exception as e:
            return {"exists": False, "error": str(e)}


class SnapchatChecker:
    """Проверка Snapchat аккаунта"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = SNAPCHAT_API_HOST
    
    async def check(self, username_or_email: str) -> dict:
        """Проверяет наличие Snapchat аккаунта"""
        if not self.api_key:
            return {"exists": False, "error": "API key not configured"}
        
        url = f"https://{self.host}/check"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        if "@" in username_or_email:
            payload = {"email": username_or_email}
        else:
            payload = {"username": username_or_email}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_value = data.get("result", "")
                        exists = data.get("exists", False) or data.get("found", False) or (result_value and str(result_value).lower() == "true")
                        return {
                            "exists": bool(exists),
                            "error": None
                        }
                    else:
                        return {"exists": False, "error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"exists": False, "error": "Request timeout"}
        except Exception as e:
            return {"exists": False, "error": str(e)}


class XChecker:
    """Проверка X (Twitter) аккаунта"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = X_API_HOST
    
    async def check(self, username_or_email: str) -> dict:
        """Проверяет наличие X (Twitter) аккаунта"""
        if not self.api_key:
            return {"exists": False, "error": "API key not configured"}
        
        url = f"https://{self.host}/check"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        if "@" in username_or_email:
            payload = {"email": username_or_email}
        else:
            payload = {"username": username_or_email}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_value = data.get("result", "")
                        exists = data.get("exists", False) or data.get("found", False) or (result_value and str(result_value).lower() == "true")
                        return {
                            "exists": bool(exists),
                            "error": None
                        }
                    else:
                        return {"exists": False, "error": f"API returned status {response.status}"}
        except asyncio.TimeoutError:
            return {"exists": False, "error": "Request timeout"}
        except Exception as e:
            return {"exists": False, "error": str(e)}
