"""Сервис проверки WhatsApp через различные API"""
import aiohttp
import asyncio
import logging
from config import (
    RAPIDAPI_KEY, WHATSAPP_API_HOST,
    CHECKNUMBER_API_KEY, IDENFY_API_KEY, WHATSAPP_API_PROVIDER,
    PROXY_URL
)

# Поддержка SOCKS прокси
try:
    from aiohttp_socks import ProxyConnector
    SOCKS_SUPPORT = True
except ImportError:
    SOCKS_SUPPORT = False
    ProxyConnector = None

logger = logging.getLogger(__name__)


class WhatsAppChecker:
    """Проверка наличия WhatsApp на номере"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.host = WHATSAPP_API_HOST
        # PROXY_URL может быть пустой строкой, проверяем явно
        self.proxy_url = PROXY_URL if PROXY_URL and PROXY_URL.strip() else None
        
        # Задержка между проверками WhatsApp (1.05 секунды между всеми проверками)
        self.check_delay_seconds = 1.05
        self.last_check_time = None
        self._lock = asyncio.Lock()  # Lock для синхронизации времени между параллельными вызовами
        
        # Логируем для отладки
        if self.proxy_url:
            # Скрываем пароль в логах
            proxy_log = self.proxy_url.split('@')[-1] if '@' in self.proxy_url else self.proxy_url
            logger.info(f"WhatsAppChecker initialized with proxy: {proxy_log}")
        else:
            logger.warning(f"WhatsAppChecker initialized WITHOUT proxy. PROXY_URL from config: '{PROXY_URL}' (empty={not PROXY_URL or not PROXY_URL.strip()})")
    
    # ============================================================================
    # CheckNumber.ai и старые методы закомментированы (временно отключены)
    # Используется только RapidAPI /WhatsappNumberHasItWithToken endpoint
    # API: whatsapp-number-validator3.p.rapidapi.com
    # ============================================================================
    
    """
    # Закомментированные методы CheckNumber.ai и iDenfy:
    # Весь код CheckNumber.ai и iDenfy временно отключен
    # Используется только RapidAPI /WhatsappNumberHasItWithToken endpoint
    """
    
    async def check(self, phone: str, max_retries: int = 3) -> dict:
        """
        Проверяет наличие WhatsApp на номере через RapidAPI
        
        Args:
            phone: Телефонный номер для проверки
            max_retries: Максимальное количество попыток при ошибке 429
            
        Returns:
            dict: Результаты проверки {valid: bool, error: str}
        """
        if not self.api_key:
            return {"error": "RapidAPI key not configured"}
        
        # Убираем все нецифровые символы (только цифры, как в примере: "447984231120")
        import re
        phone_clean = re.sub(r'\D+', '', phone)
        
        # Endpoint согласно документации: /WhatsappNumberHasItWithToken
        url = f"https://{self.host}/WhatsappNumberHasItWithToken"
        
        # Payload в формате JSON: {"phone_number":"447984231120"}
        payload = {
            "phone_number": phone_clean
        }
        
        headers = {
            "X-RapidAPI-Host": self.host,
            "X-RapidAPI-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Настраиваем прокси если он указан
        connector = None
        proxy = None
        
        # Проверяем прокси (явная проверка на None и пустую строку)
        if self.proxy_url and self.proxy_url.strip():
            # Проверяем тип прокси
            if self.proxy_url.startswith(('socks5://', 'socks4://')):
                # SOCKS прокси - используем ProxyConnector
                if SOCKS_SUPPORT:
                    try:
                        connector = ProxyConnector.from_url(self.proxy_url)
                        proxy_info = self.proxy_url.split('@')[-1] if '@' in self.proxy_url else self.proxy_url
                        logger.info(f"WhatsApp check using SOCKS proxy: {proxy_info}")
                    except Exception as e:
                        logger.error(f"Failed to create SOCKS proxy connector: {e}")
                        connector = None
                else:
                    logger.warning("SOCKS proxy specified but aiohttp-socks not installed. Install it with: pip install aiohttp-socks")
            else:
                # HTTP/HTTPS прокси - используем стандартный параметр proxy
                proxy = self.proxy_url
                proxy_info = self.proxy_url.split('@')[-1] if '@' in self.proxy_url else self.proxy_url
                logger.info(f"WhatsApp check using HTTP proxy: {proxy_info}")
        else:
            logger.warning(f"WhatsApp check without proxy. self.proxy_url = '{self.proxy_url}'")
        
        # Задержка между проверками WhatsApp (1.05 секунды между всеми проверками)
        # Используем lock только для синхронизации времени, задержку делаем вне lock
        import time
        wait_time = 0
        
        async with self._lock:
            current_time = time.time()
            if self.last_check_time is not None:
                elapsed = current_time - self.last_check_time
                if elapsed < self.check_delay_seconds:
                    wait_time = self.check_delay_seconds - elapsed
                else:
                    wait_time = 0
        
        # Выполняем задержку вне lock, чтобы не блокировать другие проверки слишком долго
        if wait_time > 0:
            logger.debug(f"WhatsApp check: waiting {wait_time:.3f}s before check (delay: {self.check_delay_seconds}s)")
            await asyncio.sleep(wait_time)
        
        # Логируем детали запроса
        logger.debug(f"WhatsApp check request: POST {url}, phone={phone_clean}, proxy={'enabled' if (connector or proxy) else 'disabled'}")
        
        # Retry логика для обработки 429 ошибок
        for attempt in range(max_retries):
            try:
                # Пересоздаем connector при каждом retry, чтобы избежать "Session is closed"
                # Это особенно важно для SOCKS прокси
                current_connector = None
                current_proxy = None
                
                if self.proxy_url and self.proxy_url.strip():
                    if self.proxy_url.startswith(('socks5://', 'socks4://')):
                        # SOCKS прокси - пересоздаем connector при каждом retry
                        if SOCKS_SUPPORT:
                            try:
                                current_connector = ProxyConnector.from_url(self.proxy_url)
                            except Exception as e:
                                logger.debug(f"Failed to recreate SOCKS connector on retry attempt {attempt + 1}: {e}")
                                # Если не удалось пересоздать, пробуем использовать оригинальный
                                current_connector = connector
                        else:
                            current_connector = connector
                    else:
                        # HTTP/HTTPS прокси - используем параметр proxy
                        current_proxy = self.proxy_url
                        current_connector = None
                else:
                    current_connector = None
                    current_proxy = None
                
                async with aiohttp.ClientSession(connector=current_connector) as session:
                    async with session.post(url, json=payload, headers=headers, proxy=current_proxy, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            # Ответ должен быть JSON
                            response_text = await response.text()
                            response_text = response_text.strip()
                            
                            # Парсим JSON ответ
                            try:
                                import json
                                response_data = json.loads(response_text)
                                
                                # Ищем поле с результатом (может быть 'has_whatsapp', 'valid', 'exists', 'result', 'is_valid' и т.д.)
                                is_valid = False
                                if isinstance(response_data, dict):
                                    # Пробуем разные возможные поля
                                    is_valid = (
                                        response_data.get('has_whatsapp', False) or
                                        response_data.get('valid', False) or
                                        response_data.get('exists', False) or
                                        response_data.get('result', False) or
                                        response_data.get('is_valid', False) or
                                        response_data.get('status', '').lower() == 'valid'
                                    )
                                    
                                    # Если значение строка, проверяем как булево
                                    if isinstance(is_valid, str):
                                        is_valid = is_valid.lower() in ['true', '1', 'yes', 'valid']
                                else:
                                    is_valid = bool(response_data)
                                
                                logger.info(f"WhatsApp check via RapidAPI ({self.host}): {phone_clean} -> valid={is_valid} (response: {response_text[:200]})")
                                
                                # Обновляем время последней проверки после успешного запроса
                                async with self._lock:
                                    self.last_check_time = time.time()
                                
                                return {
                                    "valid": is_valid,
                                    "error": None
                                }
                            except (json.JSONDecodeError, ValueError) as e:
                                # Если не удалось распарсить JSON
                                logger.warning(f"WhatsApp check: Failed to parse JSON response: {e}, raw response: {response_text[:200]}")
                                # Пробуем как строку
                                is_valid = response_text.lower() in ['true', '1', 'yes']
                                return {
                                    "valid": is_valid,
                                    "error": None
                                }
                        elif response.status == 429:
                            # Ошибка 429 - Rate limit exceeded, нужно подождать
                            try:
                                error_text = await response.text()
                                import json
                                try:
                                    error_data = json.loads(error_text)
                                    retry_after_ms = error_data.get('retry_after_ms', 1000)  # По умолчанию 1 секунда
                                    retry_after_sec = retry_after_ms / 1000.0
                                except (json.JSONDecodeError, ValueError, KeyError):
                                    # Если не удалось распарсить, используем экспоненциальную задержку
                                    retry_after_sec = (attempt + 1) * 2  # 2, 4, 6 секунд
                                
                                if attempt < max_retries - 1:
                                    logger.warning(f"WhatsApp check rate limit (429) for {phone_clean}, attempt {attempt + 1}/{max_retries}, waiting {retry_after_sec:.1f}s before retry...")
                                    await asyncio.sleep(retry_after_sec)
                                    continue  # Повторяем попытку
                                else:
                                    error_msg = f"Status 429 (Rate limit exceeded): {error_text}"
                                    logger.error(f"WhatsApp check rate limit exceeded after {max_retries} attempts: {error_msg}")
                                    # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                                    async with self._lock:
                                        self.last_check_time = time.time()
                                    return {
                                        "valid": False,
                                        "error": error_msg
                                    }
                            except Exception as e:
                                logger.error(f"Error processing 429 response: {e}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep((attempt + 1) * 2)
                                    continue
                                # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                                async with self._lock:
                                    self.last_check_time = time.time()
                                return {
                                    "valid": False,
                                    "error": f"Status 429 (Rate limit exceeded)"
                                }
                        elif response.status == 451:
                            # Ошибка 451 - геоблокировка (прокси может не работать)
                            try:
                                error_text = await response.text()
                                error_msg = f"Status 451 (Geo-blocked): {error_text}"
                            except:
                                error_msg = "Status 451 (Geo-blocked): RapidAPI service unavailable in your location"
                            
                            proxy_status = "with proxy" if (current_connector or current_proxy) else "without proxy"
                            logger.warning(f"WhatsApp check error via RapidAPI ({self.host}) {proxy_status}: {error_msg}")
                            logger.warning(f"Proxy configuration: connector={'set' if current_connector else 'None'}, proxy={'set' if current_proxy else 'None'}")
                            # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                            async with self._lock:
                                self.last_check_time = time.time()
                            return {
                                "valid": False,
                                "error": error_msg
                            }
                        else:
                            # Другие ошибки от API
                            try:
                                error_text = await response.text()
                                error_msg = f"Status {response.status}: {error_text}"
                            except:
                                error_msg = f"Status {response.status}"
                            
                            logger.warning(f"WhatsApp check error via RapidAPI ({self.host}): {error_msg}")
                            # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                            async with self._lock:
                                self.last_check_time = time.time()
                            return {
                                "valid": False,
                                "error": error_msg
                            }
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"WhatsApp check timeout for {phone_clean}, attempt {attempt + 1}/{max_retries}, retrying...")
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                else:
                    error_msg = "Timeout"
                    logger.warning(f"WhatsApp check timeout via RapidAPI ({self.host}) after {max_retries} attempts")
                    # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                    async with self._lock:
                        self.last_check_time = time.time()
                    return {"valid": False, "error": error_msg}
            except Exception as e:
                error_str = str(e)
                # Обрабатываем ошибку "Session is closed" - пересоздаем сессию и повторяем
                if "Session is closed" in error_str or "session" in error_str.lower() or "closed" in error_str.lower():
                    logger.debug(f"WhatsApp check session error (will retry): {error_str}")
                    if attempt < max_retries - 1:
                        # Небольшая задержка перед повторной попыткой
                        await asyncio.sleep(0.5)
                        continue  # Повторяем попытку с новой сессией
                    else:
                        # Если все попытки исчерпаны, обновляем время и возвращаем ошибку
                        async with self._lock:
                            self.last_check_time = time.time()
                        return {"valid": False, "error": f"Session error after {max_retries} attempts: {error_str}"}
                
                if attempt < max_retries - 1:
                    logger.warning(f"WhatsApp check exception for {phone_clean}, attempt {attempt + 1}/{max_retries}: {e}, retrying...")
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                else:
                    error_msg = str(e)
                    logger.warning(f"WhatsApp check exception via RapidAPI ({self.host}): {error_msg}")
                    # Обновляем время даже при ошибке, чтобы не блокировать следующие проверки
                    async with self._lock:
                        self.last_check_time = time.time()
                    return {"valid": False, "error": error_msg}
        
        # Если дошли сюда, значит все попытки исчерпаны
        # Обновляем время, чтобы не блокировать следующие проверки
        async with self._lock:
            self.last_check_time = time.time()
        return {"valid": False, "error": "All retry attempts failed"}
    
    # ============================================================================
    # CheckNumber.ai код закомментирован (временно отключен)
    # ============================================================================
    
    # async def _check_via_checknumber(self, phone_clean: str) -> dict:
