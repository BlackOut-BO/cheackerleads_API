"""Telegram бот для проверки лидов"""
import logging
import asyncio
import json
import csv
import io
import tempfile
import os
import re
from typing import Dict, List, Tuple, Optional
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

from config import TELEGRAM_BOT_TOKEN, BOT_PASSWORD
from services.lead_checker import LeadChecker
from utils.data_parser import LeadParser
from utils.csv_processor import CSVProcessor
from utils.file_processor import FileProcessor
from utils.auth import AuthManager
from utils.check_auth import require_auth

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
lead_checker = LeadChecker()
parser = LeadParser()
auth_manager = AuthManager()  # Менеджер авторизации

# Хранилище результатов проверки (для кнопок "Подробнее")
# Ключ: user_id, значение: список результатов
check_results_storage: Dict[int, List[Dict]] = {}

# Инициализация бота и диспетчера (будут созданы в main)
bot: Bot = None
dp: Dispatcher = None


def format_check_result(result: Dict, lead_num: int = None, detailed: bool = True, friendly: bool = True) -> str:
    """Форматирует результат проверки для вывода"""
    lead = result.get("lead", {})
    lead_info = []
    if lead.get("ip"):
        lead_info.append(f"ip={lead['ip']}")
    if lead.get("email"):
        lead_info.append(f"email={lead['email']}")
    if lead.get("phone"):
        lead_info.append(f"phone={lead['phone']}")
    
    lead_str = " | ".join(lead_info)
    lead_num_str = f"Lead #{lead_num}: " if lead_num else ""
    
    verdict = result.get("verdict", "unknown")
    score = result.get("final_score", 0)
    
    # Определяем статус лида
    if verdict == "clean":
        status_emoji = "✅"
        status_text = "ФРЕНДЛИ ЛИД"
        status_color = "🟢"
    elif verdict == "risky":
        status_emoji = "⚠️"
        status_text = "РИСКОВАННЫЙ ЛИД"
        status_color = "🟡"
    else:  # spam
        status_emoji = "🚫"
        status_text = "СПАМ ЛИД"
        status_color = "🔴"
    
    if friendly:
        text = f"{status_color} <b>{status_text}</b>\n\n"
        text += f"<b>Данные лида:</b>\n{lead_str}\n\n"
        text += f"<b>Вердикт:</b> {verdict.upper()} (оценка: {score:.2f}/100)\n\n"
    else:
        text = f"<b>{lead_num_str}{lead_str}</b>\n"
        text += f"Verdict: <b>{verdict.upper()}</b> (score: {score:.2f})\n\n"
    
    if friendly:
        # Дружелюбный формат для одиночного режима
        text += f"<b>Детали проверки:</b>\n\n"
        
        # Оценки по категориям
        ip_score = result.get('ip_score')
        email_score = result.get('email_score')
        phone_score = result.get('phone_score')
        
        text += f"<b>Оценки риска:</b>\n"
        if ip_score is not None:
            ip_status = "✅ Низкий" if ip_score < 30 else "⚠️ Средний" if ip_score < 70 else "🚫 Высокий"
            text += f"• IP адрес: {ip_score:.1f}/100 {ip_status}\n"
        else:
            ip_data = result.get('ip_data') or {}
            ip_error = ip_data.get('error', 'Не проверено') if isinstance(ip_data, dict) else 'Не проверено'
            text += f"• IP адрес: ❌ {ip_error}\n"
        
        if email_score is not None:
            email_status = "✅ Низкий" if email_score < 30 else "⚠️ Средний" if email_score < 70 else "🚫 Высокий"
            text += f"• Email: {email_score:.1f}/100 {email_status}\n"
        else:
            email_data = result.get('email_data') or {}
            email_error = email_data.get('error', 'Не проверено') if isinstance(email_data, dict) else 'Не проверено'
            text += f"• Email: ❌ {email_error}\n"
        
        if phone_score is not None:
            phone_status = "✅ Низкий" if phone_score < 30 else "⚠️ Средний" if phone_score < 70 else "🚫 Высокий"
            text += f"• Телефон: {phone_score:.1f}/100 {phone_status}\n"
        else:
            phone_data = result.get('phone_data') or {}
            phone_error = phone_data.get('error', 'Не проверено') if isinstance(phone_data, dict) else 'Не проверено'
            text += f"• Телефон: ❌ {phone_error}\n"
        
        text += f"\n"
        
        # WhatsApp проверка
        if result.get("whatsapp_data"):
            whatsapp_valid = result["whatsapp_data"].get("valid", False)
            whatsapp_status = "✅ Валидный" if whatsapp_valid else "❌ Невалидный"
            text += f"<b>WhatsApp:</b> {whatsapp_status}\n"
        
        # Социальные сети
        social_data = result.get("social_data", {})
        if social_data:
            text += f"\n<b>Социальные сети:</b>\n"
            social_found = []
            social_not_found = []
            for social_name, social_result in social_data.items():
                if not social_result.get("error"):
                    exists = social_result.get("exists", False)
                    if exists:
                        social_found.append(social_name.capitalize())
                    else:
                        social_not_found.append(social_name.capitalize())
            
            if social_found:
                text += f"✅ Найдено: {', '.join(social_found)}\n"
            if social_not_found:
                text += f"❌ Не найдено: {', '.join(social_not_found)}\n"
    else:
        # Технический формат
        text += f"<b>Проверки:</b>\n"
        ip_score = result.get('ip_score')
        email_score = result.get('email_score')
        phone_score = result.get('phone_score')
        
        if ip_score is not None:
            text += f"• IP: {ip_score}\n"
        else:
            ip_data = result.get('ip_data') or {}
            ip_error = ip_data.get('error', 'Не проверено') if isinstance(ip_data, dict) else 'Не проверено'
            text += f"• IP: ❌ {ip_error}\n"
        
        if email_score is not None:
            text += f"• Email: {email_score}\n"
        else:
            email_data = result.get('email_data') or {}
            email_error = email_data.get('error', 'Не проверено') if isinstance(email_data, dict) else 'Не проверено'
            text += f"• Email: ❌ {email_error}\n"
        
        if phone_score is not None:
            text += f"• Phone: {phone_score}\n"
        else:
            phone_data = result.get('phone_data') or {}
            phone_error = phone_data.get('error', 'Не проверено') if isinstance(phone_data, dict) else 'Не проверено'
            text += f"• Phone: ❌ {phone_error}\n"
        
        text += f"\nThresholds: risky>={50}, spam>={75}\n"
        
        # WhatsApp проверка
        if result.get("whatsapp_data"):
            whatsapp_valid = result["whatsapp_data"].get("valid", False)
            text += f"WhatsApp: {'✓ Valid' if whatsapp_valid else '✗ Invalid'}\n"
        
        # Социальные сети
        social_data = result.get("social_data", {})
        if social_data:
            text += f"\nSocial networks:\n"
            for social_name, social_result in social_data.items():
                if not social_result.get("error"):
                    exists = social_result.get("exists", False)
                    text += f"  {social_name.capitalize()}: {'✓ Found' if exists else '✗ Not found'}\n"
    
    # Причины (только для детального режима)
    if detailed:
        reasons = result.get("reasons", [])
        if reasons:
            text += f"\n- Reasons:\n"
            for reason in reasons[:20]:  # Ограничиваем количество причин
                text += f"  • {reason}\n"
    
    return text


def format_summary(results: List[Dict]) -> Tuple[str, InlineKeyboardMarkup]:
    """Форматирует сводку по нескольким лидам с группировкой по вердиктам и кнопками"""
    text = f"📊 <b>Сводка по проверке</b>\n\n"
    text += f"Всего проверено лидов: {len(results)}\n\n"
    
    # Группируем по вердиктам
    clean_leads = []
    risky_leads = []
    spam_leads = []
    
    for result in results:
        if not result:
            continue
        verdict = result.get("verdict", "clean")
        if verdict == "clean":
            clean_leads.append(result)
        elif verdict == "risky":
            risky_leads.append(result)
        elif verdict == "spam":
            spam_leads.append(result)
    
    # Статистика
    text += f"<b>Статистика:</b>\n"
    text += f"✅ Clean: {len(clean_leads)}\n"
    text += f"⚠️ Risky: {len(risky_leads)}\n"
    text += f"🚫 Spam: {len(spam_leads)}\n\n"
    
    # Создаем кнопки для детального просмотра (по 2 в ряд)
    buttons = []
    current_row = []
    
    # Детальная информация по каждой категории (в порядке SPAM -> RISKY -> CLEAN)
    if spam_leads:
        text += f"🚫 <b>SPAM ({len(spam_leads)}):</b>\n"
        for i, result in enumerate(spam_leads, 1):
            lead = result.get("lead", {}) or {}
            lead_info = []
            if lead.get("ip"):
                lead_info.append(f"ip={lead['ip']}")
            if lead.get("email"):
                lead_info.append(f"email={lead['email']}")
            if lead.get("phone"):
                lead_info.append(f"phone={lead['phone']}")
            lead_str = " | ".join(lead_info)
            score = result.get("final_score", 0)
            lead_num = result.get("lead_number", 0)
            text += f"  {i}. {lead_str} (score: {score:.2f})\n"
            # Добавляем кнопку в текущий ряд
            current_row.append(InlineKeyboardButton(
                text=f"📋 #{lead_num}",
                callback_data=f"detail_{lead_num}"
            ))
            # Если в ряду 2 кнопки, добавляем ряд и начинаем новый
            if len(current_row) == 2:
                buttons.append(current_row)
                current_row = []
        text += "\n"
    
    if risky_leads:
        text += f"⚠️ <b>RISKY ({len(risky_leads)}):</b>\n"
        for i, result in enumerate(risky_leads, 1):
            lead = result.get("lead", {}) or {}
            lead_info = []
            if lead.get("ip"):
                lead_info.append(f"ip={lead['ip']}")
            if lead.get("email"):
                lead_info.append(f"email={lead['email']}")
            if lead.get("phone"):
                lead_info.append(f"phone={lead['phone']}")
            lead_str = " | ".join(lead_info)
            score = result.get("final_score", 0)
            lead_num = result.get("lead_number", 0)
            text += f"  {i}. {lead_str} (score: {score:.2f})\n"
            # Добавляем кнопку в текущий ряд
            current_row.append(InlineKeyboardButton(
                text=f"📋 #{lead_num}",
                callback_data=f"detail_{lead_num}"
            ))
            # Если в ряду 2 кнопки, добавляем ряд и начинаем новый
            if len(current_row) == 2:
                buttons.append(current_row)
                current_row = []
        text += "\n"
    
    if clean_leads:
        text += f"✅ <b>CLEAN ({len(clean_leads)}):</b>\n"
        for i, result in enumerate(clean_leads, 1):
            lead = result.get("lead", {}) or {}
            lead_info = []
            if lead.get("ip"):
                lead_info.append(f"ip={lead['ip']}")
            if lead.get("email"):
                lead_info.append(f"email={lead['email']}")
            if lead.get("phone"):
                lead_info.append(f"phone={lead['phone']}")
            lead_str = " | ".join(lead_info)
            score = result.get("final_score", 0)
            lead_num = result.get("lead_number", 0)
            text += f"  {i}. {lead_str} (score: {score:.2f})\n"
            # Добавляем кнопку в текущий ряд
            current_row.append(InlineKeyboardButton(
                text=f"📋 #{lead_num}",
                callback_data=f"detail_{lead_num}"
            ))
            # Если в ряду 2 кнопки, добавляем ряд и начинаем новый
            if len(current_row) == 2:
                buttons.append(current_row)
                current_row = []
    
    # Добавляем оставшиеся кнопки, если есть
    if current_row:
        buttons.append(current_row)
    
    # Добавляем кнопку "Обновить меню" на отдельной строке
    buttons.append([InlineKeyboardButton(text="🔄 Обновить меню", callback_data="refresh")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    return text, keyboard


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создает главную клавиатуру с кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📖 Справка", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ],
        [
            InlineKeyboardButton(text="📤 Загрузить файл", callback_data="upload_file"),
            InlineKeyboardButton(text="✍️ Ввести данные", callback_data="input_data")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить меню", callback_data="refresh")
        ]
    ])
    return keyboard


async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем авторизацию
    if not auth_manager.is_authorized(user_id):
        text = (
            "🔐 <b>Требуется авторизация</b>\n\n"
            "Бот доступен только администраторам."
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
        return
    
    welcome_text = """🤖 <b>Checkerleads Bot</b>

Я помогаю проверять лиды на валидность и риски.

<b>Возможности:</b>
✅ Проверка email, IP и телефона
✅ Проверка WhatsApp
✅ Проверка социальных сетей (Facebook, Google, Instagram, Snapchat, X)
✅ Оценка рисков и вердикт (clean/risky/spam)

<b>Как использовать:</b>
1. Нажмите кнопку "Загрузить файл" для загрузки файла
2. Или нажмите "Ввести данные" и отправьте текст с лидами

Примеры формата:
• email=test@example.com | ip=192.168.1.1 | phone=+1234567890
• test@example.com 192.168.1.1 +1234567890
• Просто текст с данными - я распознаю автоматически"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)


@require_auth(auth_manager)
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await show_help(message)


async def show_help(message_or_query):
    """Показывает справку"""
    help_text = """📖 <b>Справка по использованию бота</b>

<b>Форматы данных:</b>

1. <b>CSV файл</b> - загрузите файл с колонками:
   - email, ip, phone (или любые другие названия)
   - Бот автоматически распознает данные

2. <b>Ручной ввод</b> - отправьте текст в любом формате:
   • email=test@example.com | ip=192.168.1.1 | phone=+1234567890
   • test@example.com 192.168.1.1 +1234567890
   • Просто текст - бот распознает автоматически

<b>Результаты проверки:</b>
• <b>clean</b> - выглядит нормально (score &lt; 50)
• <b>risky</b> - есть заметные риски (score 50-74)
• <b>spam</b> - очень похоже на спам/мошенничество (score &gt;= 75)

<b>Проверяемые данные:</b>
✅ Email (Abstract API)
✅ IP (ipdata.co)
✅ Телефон (numverify)
✅ WhatsApp (RapidAPI)
✅ Facebook, Google, Instagram, Snapchat, X (RapidAPI)"""
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_text(help_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
        except TelegramBadRequest:
            # Если сообщение нельзя редактировать (например, это документ), отправляем новое
            await message_or_query.message.answer(help_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await message_or_query.answer(help_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)


async def show_about(message_or_query):
    """Показывает информацию о боте"""
    about_text = """ℹ️ <b>О боте Checkerleads</b>

Этот бот предназначен для комплексной проверки лидов на валидность и риски.

<b>Что проверяется:</b>
• Email адреса на валидность и качество
• IP адреса на угрозы и анонимность
• Телефонные номера на валидность и тип линии
• Наличие WhatsApp на номере
• Наличие аккаунтов в социальных сетях

<b>Оценка рисков:</b>
Бот автоматически оценивает каждый лид по шкале 0-100 и выдает вердикт:
• clean - безопасный лид
• risky - есть риски
• spam - подозрительный лид

Используйте кнопки ниже для навигации."""
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_text(about_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
        except TelegramBadRequest:
            # Если сообщение нельзя редактировать (например, это документ), отправляем новое
            await message_or_query.message.answer(about_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await message_or_query.answer(about_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)


async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки Справка"""
    await show_help(callback)
    await callback.answer()


@require_auth(auth_manager)
async def callback_about(callback: CallbackQuery):
    """Обработчик кнопки О боте"""
    await show_about(callback)
    await callback.answer()


@require_auth(auth_manager)
async def callback_upload_file(callback: CallbackQuery):
    """Обработчик кнопки Загрузить файл"""
    text = (
        "📤 <b>Загрузка файла</b>\n\n"
        "Пожалуйста, отправьте файл с лидами в любом формате:\n\n"
        "Поддерживаемые форматы:\n"
        "• CSV (.csv)\n"
        "• Excel (.xlsx, .xls)\n"
        "• TXT (.txt)\n"
        "• JSON (.json)\n\n"
        "Бот автоматически распознает данные и формат файла."
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        # Если сообщение нельзя редактировать (например, это документ), отправляем новое
        await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer("Теперь отправьте файл")


@require_auth(auth_manager)
async def callback_input_data(callback: CallbackQuery):
    """Обработчик кнопки Ввести данные"""
    text = (
        "✍️ <b>Ввод данных</b>\n\n"
        "Отправьте данные лидов в любом формате:\n\n"
        "Примеры:\n"
        "• email=test@example.com | ip=192.168.1.1 | phone=+1234567890\n"
        "• test@example.com 192.168.1.1 +1234567890\n"
        "• Просто текст - бот распознает автоматически"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        # Если сообщение нельзя редактировать (например, это документ), отправляем новое
        await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer("Теперь отправьте данные")


@require_auth(auth_manager)
async def callback_refresh(callback: CallbackQuery):
    """Обработчик кнопки Обновить меню"""
    welcome_text = """🤖 <b>Checkerleads Bot</b>

Я помогаю проверять лиды на валидность и риски.

<b>Возможности:</b>
✅ Проверка email, IP и телефона
✅ Проверка WhatsApp
✅ Проверка социальных сетей (Facebook, Google, Instagram, Snapchat, X)
✅ Оценка рисков и вердикт (clean/risky/spam)

<b>Как использовать:</b>
1. Нажмите кнопку "Загрузить файл" для загрузки файла
2. Или нажмите "Ввести данные" и отправьте текст с лидами

Примеры формата:
• email=test@example.com | ip=192.168.1.1 | phone=+1234567890
• test@example.com 192.168.1.1 +1234567890
• Просто текст с данными - я распознаю автоматически"""
    
    try:
        await callback.message.edit_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        # Если сообщение нельзя редактировать (например, это документ), отправляем новое
        await callback.message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer("Меню обновлено")


@require_auth(auth_manager)
async def callback_detail(callback: CallbackQuery):
    """Обработчик кнопки Подробнее для конкретного лида - показывает JSON"""
    try:
        # Извлекаем номер лида из callback_data
        lead_num = int(callback.data.split("_")[1])
        
        # Получаем результаты для этого пользователя
        user_id = callback.from_user.id
        results = check_results_storage.get(user_id, [])
        
        if not results:
            await callback.answer("Результаты проверки не найдены. Пожалуйста, выполните проверку снова.")
            return
        
        # Находим нужный лид
        target_result = None
        for result in results:
            if result and result.get("lead_number") == lead_num:
                target_result = result
                break
        
        if not target_result:
            await callback.answer("Лид не найден.")
            return
        
        # Форматируем JSON результат
        json_result = json.dumps(target_result, indent=2, ensure_ascii=False)
        
        # Отправляем JSON результат
        if len(json_result) > 4000:
            parts = [json_result[i:i+4000] for i in range(0, len(json_result), 4000)]
            for part in parts:
                await callback.message.answer(f"<pre>{part}</pre>", parse_mode=ParseMode.HTML)
        else:
            await callback.message.answer(f"<pre>{json_result}</pre>", parse_mode=ParseMode.HTML)
        
        await callback.answer(f"JSON лида #{lead_num}")
    
    except Exception as e:
        logger.error(f"Ошибка при показе деталей: {e}")
        await callback.answer("Ошибка при загрузке деталей")


async def handle_document(message: Message):
    """Обработчик загрузки файлов"""
    user_id = message.from_user.id
    
    # Проверяем авторизацию
    if not auth_manager.is_authorized(user_id):
        await message.answer(
            "❌ <b>Требуется авторизация</b>\n\n"
            "Бот доступен только администраторам.",
            parse_mode=ParseMode.HTML
        )
        return
    
    document = message.document
    
    if not document:
        await message.answer("❌ Файл не найден.", reply_markup=get_main_keyboard())
        return
    
    # Получаем имя файла
    file_name = document.file_name or "unknown"
    file_name_lower = file_name.lower()
    
    # Проверяем поддерживаемые форматы
    supported_formats = ['.csv', '.xlsx', '.xls', '.txt', '.json']
    if not any(file_name_lower.endswith(ext) for ext in supported_formats):
        await message.answer(
            "❌ Неподдерживаемый формат файла.\n\n"
            "Поддерживаемые форматы:\n"
            "• CSV (.csv)\n"
            "• Excel (.xlsx, .xls)\n"
            "• TXT (.txt)\n"
            "• JSON (.json)",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Скачиваем файл
    try:
        file = await bot.get_file(document.file_id)
        file_bytes_io = await bot.download_file(file.file_path)
        file_bytes = file_bytes_io.read()
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла: {e}")
        await message.answer(f"❌ Ошибка при скачивании файла: {str(e)}", reply_markup=get_main_keyboard())
        return
    
    # Парсим файл любого формата
    try:
        # Определяем тип файла и парсим
        leads, fieldnames, original_rows, delimiter = FileProcessor.parse_file(file_bytes, file_name)
        
        # Определяем, является ли это табличным форматом (CSV, Excel)
        file_type = FileProcessor.detect_file_type(file_name)
        is_table_format = file_type in ['csv', 'excel']
        
        if not leads:
            await message.answer("❌ Не удалось найти данные в файле.", reply_markup=get_main_keyboard())
            return
        
        await message.answer(f"✅ Найдено лидов: {len(leads)}\n🔄 Начинаю проверку...")
        
        # Логируем найденные данные для отладки
        logger.info(f"Parsed {len(leads)} leads from CSV")
        for i, lead in enumerate(leads[:3], 1):  # Логируем первые 3 для отладки
            logger.debug(f"Lead {i}: email={lead.get('email')}, ip={lead.get('ip')}, phone={lead.get('phone')}")
        
        # Проверяем лиды
        results = await lead_checker.check_leads(leads, check_social=True)
        
        # Сохраняем результаты для пользователя (для кнопок)
        check_results_storage[message.from_user.id] = results
        
        if is_table_format and original_rows:
            # Для CSV - создаем отредактированный файл
            csv_bytes = CSVProcessor.create_csv_with_results(
                original_rows, 
                fieldnames, 
                results,
                file_name,
                delimiter
            )
            
            # Определяем расширение для выходного файла (всегда CSV)
            output_filename = file_name.rsplit('.', 1)[0] + '_checked.csv' if '.' in file_name else f"checked_{file_name}.csv"
            
            # Отправляем отредактированный CSV файл
            csv_file = BufferedInputFile(csv_bytes, filename=output_filename)
            await message.answer_document(
                document=csv_file,
                caption=f"✅ Проверка завершена! Обработано: {len(results)} лидов\n📊 Все результаты сохранены в файле",
                reply_markup=get_main_keyboard()
            )
            
            # Для CSV файлов сводку не отправляем - она уже в файле
            # Сохраняем результаты для кнопок "Подробнее" (если понадобится)
            check_results_storage[message.from_user.id] = results
        else:
            # Для TXT или одного лида - все в файле (текст + JSON)
            if len(results) == 1:
                result = results[0]
                lead_num = result.get("lead_number", 0)
                formatted_result = format_check_result(result, lead_num, detailed=True, friendly=False)
                
                # Убираем HTML теги из текстового результата для файла
                import re
                text_result = re.sub(r'<[^>]+>', '', formatted_result)
                
                # Создаем JSON результат
                json_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                
                # Формируем содержимое файла: текст + разделитель + JSON
                file_content = f"{text_result}\n\n{'='*60}\n\nJSON Result:\n\n{json_result}"
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # Читаем файл и отправляем
                    with open(tmp_file_path, 'rb') as f:
                        result_file = BufferedInputFile(f.read(), filename=f"lead_{lead_num}_result.txt")
                        await message.answer_document(
                            document=result_file,
                            caption=f"📄 Результат проверки Lead #{lead_num}",
                            reply_markup=get_main_keyboard()
                        )
                finally:
                    # Удаляем временный файл
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
            else:
                # Для TXT файлов с несколькими лидами - отправляем сводку
                summary, keyboard = format_summary(results)
                # Проверяем длину сводки и разбиваем на части, если нужно
                if len(summary) > 4000:
                    # Разбиваем сводку на части по разделам
                    parts = summary.split('\n\n')
                    current_part = ""
                    for part in parts:
                        if len(current_part) + len(part) + 2 > 4000:
                            if current_part:
                                await message.answer(current_part, parse_mode=ParseMode.HTML)
                            current_part = part
                        else:
                            current_part += "\n\n" + part if current_part else part
                    if current_part:
                        # Последняя часть с клавиатурой
                        await message.answer(current_part, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                else:
                    await message.answer(summary, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            
            await message.answer(f"✅ Проверка завершена! Обработано лидов: {len(results)}", reply_markup=get_main_keyboard())
    
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await message.answer(f"❌ Ошибка при обработке файла: {str(e)}", reply_markup=get_main_keyboard())


async def handle_text(message: Message):
    """Обработчик текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Пропускаем команды
    if text.startswith('/'):
        return
    
    # Проверяем авторизацию
    if not auth_manager.is_authorized(user_id):
        await message.answer(
            "❌ <b>Доступ ограничен</b>\n\n"
            "Бот доступен только администраторам.",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Парсим текст
    try:
        # Пытаемся распознать несколько лидов
        leads = parser.parse_multiple_text(text)
        
        # Фильтруем пустые лиды
        leads = [lead for lead in leads if lead.get("email") or lead.get("ip") or lead.get("phone")]
        
        if not leads:
            await message.answer(
                "❌ Не удалось распознать данные. "
                "Пожалуйста, укажите email, IP или телефон.\n\n"
                "Пример: email=test@example.com | ip=192.168.1.1 | phone=+1234567890",
                reply_markup=get_main_keyboard()
            )
            return
        
        await message.answer(
            f"✅ Распознано лидов: {len(leads)}\n"
            f"🔄 Начинаю проверку..."
        )
        
        # Проверяем лиды
        results = await lead_checker.check_leads(leads, check_social=True)
        
        # Отправляем результаты
        if len(results) == 1:
            # Для одного лида - все в файле (текст + JSON)
            result = results[0]
            lead_num = result.get("lead_number", 0)
            formatted_result = format_check_result(result, lead_num, detailed=True, friendly=False)
            
            # Убираем HTML теги из текстового результата для файла
            text_result = re.sub(r'<[^>]+>', '', formatted_result)
            
            # Создаем JSON результат
            json_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            
            # Формируем содержимое файла: текст + разделитель + JSON
            file_content = f"{text_result}\n\n{'='*60}\n\nJSON Result:\n\n{json_result}"
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Читаем файл и отправляем
                with open(tmp_file_path, 'rb') as f:
                    result_file = BufferedInputFile(f.read(), filename=f"lead_{lead_num}_result.txt")
                    await message.answer_document(
                        document=result_file,
                        caption=f"📄 Результат проверки Lead #{lead_num}",
                        reply_markup=get_main_keyboard()
                    )
            finally:
                # Удаляем временный файл
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
        else:
            # Для нескольких лидов - создаем CSV файл
            # Сохраняем результаты для пользователя (для кнопок "Подробнее")
            check_results_storage[message.from_user.id] = results
            
            # Создаем структуру для CSV из лидов
            fieldnames = ["Email", "IP", "Phone"]
            original_rows = []
            for lead in leads:
                row = {
                    "Email": lead.get("email") or "",
                    "IP": lead.get("ip") or "",
                    "Phone": lead.get("phone") or ""
                }
                original_rows.append(row)
            
            # Создаем CSV файл с результатами
            csv_bytes = CSVProcessor.create_csv_with_results(
                original_rows,
                fieldnames,
                results,
                "manual_input.csv",
                ","
            )
            
            # Отправляем CSV файл
            csv_file = BufferedInputFile(csv_bytes, filename="checked_leads.csv")
            await message.answer_document(
                document=csv_file,
                caption=f"✅ Проверка завершена! Обработано: {len(results)} лидов\n📊 Все результаты сохранены в файле",
                reply_markup=get_main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке текста: {e}")
        await message.answer(f"❌ Ошибка при обработке: {str(e)}", reply_markup=get_main_keyboard())


async def main():
    """Запуск бота"""
    global bot, dp
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в .env файле!")
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен в .env файле!")
        print("Пожалуйста, создайте файл .env на основе env.example и заполните все необходимые ключи.")
        return
    
    # Инициализация бота и диспетчера с правильными настройками
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем обработчики
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.callback_query.register(callback_help, F.data == "help")
    dp.callback_query.register(callback_about, F.data == "about")
    dp.callback_query.register(callback_upload_file, F.data == "upload_file")
    dp.callback_query.register(callback_input_data, F.data == "input_data")
    dp.callback_query.register(callback_refresh, F.data == "refresh")
    dp.callback_query.register(callback_detail, F.data.startswith("detail_"))
    dp.message.register(handle_document, F.document)
    dp.message.register(handle_text, F.text)
    
    try:
        # Запускаем бота
        logger.info("Бот запущен...")
        print("✅ Бот успешно запущен! Ожидаю сообщений...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        print(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
