"""Middleware для проверки авторизации"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from utils.auth import AuthManager


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки авторизации пользователей"""
    
    def __init__(self, auth_manager: AuthManager):
        """
        Инициализирует middleware
        
        Args:
            auth_manager: Менеджер авторизации
        """
        self.auth_manager = auth_manager
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверяет авторизацию перед выполнением обработчика
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные события
        """
        # Получаем пользователя из события
        user = None
        if hasattr(event, 'from_user'):
            user = event.from_user
        elif hasattr(event, 'message') and event.message:
            user = event.message.from_user
        elif hasattr(event, 'callback_query') and event.callback_query:
            user = event.callback_query.from_user
        
        # Если пользователь не найден, пропускаем
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        
        # Проверяем авторизацию
        # Исключения: команда /start и обработка пароля
        if hasattr(event, 'text'):
            text = event.text
            if text and (text.startswith('/start') or text.startswith('/password')):
                return await handler(event, data)
        elif hasattr(event, 'message') and event.message and event.message.text:
            text = event.message.text
            if text.startswith('/start') or text.startswith('/password'):
                return await handler(event, data)
        
        # Если пользователь не авторизован, проверяем, не вводит ли он пароль
        if not self.auth_manager.is_authorized(user_id):
            # Если это текстовое сообщение, проверяем как пароль
            if hasattr(event, 'text') and event.text:
                password = event.text.strip()
                if self.auth_manager.check_password(password, data.get('bot_password', '')):
                    self.auth_manager.authorize_user(user_id)
                    if hasattr(event, 'answer'):
                        await event.answer(
                            "✅ Пароль принят! Теперь вы можете использовать бота.\n\n"
                            "Используйте /start для начала работы.",
                            parse_mode=ParseMode.HTML
                        )
                    return
                else:
                    if hasattr(event, 'answer'):
                        await event.answer(
                            "❌ Неверный пароль. Попробуйте еще раз.",
                            parse_mode=ParseMode.HTML
                        )
                    return
        
        # Если авторизован, выполняем обработчик
        return await handler(event, data)
