"""Декоратор для проверки авторизации"""
from functools import wraps
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from utils.auth import AuthManager


def require_auth(auth_manager: AuthManager):
    """
    Декоратор для проверки авторизации перед выполнением функции
    
    Args:
        auth_manager: Менеджер авторизации
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            # Получаем user_id из события
            user_id = None
            if isinstance(event, Message):
                user_id = event.from_user.id
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
            
            if not user_id:
                return
            
            # Проверяем авторизацию
            if not auth_manager.is_authorized(user_id):
                if isinstance(event, Message):
                    await event.answer(
                        "❌ <b>Доступ ограничен</b>\n\n"
                        "Бот доступен только администраторам.",
                        parse_mode=ParseMode.HTML
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Доступ ограничен: только админы.",
                        show_alert=True
                    )
                return
            
            # Выполняем функцию
            return await func(event, *args, **kwargs)
        
        return wrapper
    return decorator
