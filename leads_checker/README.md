# Checkerleads - Telegram Bot для проверки лидов

Telegram бот для комплексной проверки лидов на валидность и риски.

## Возможности

- ✅ Проверка email через Abstract API
- ✅ Проверка IP через ipdata.co
- ✅ Проверка телефона через numverify
- ✅ Проверка WhatsApp через RapidAPI
- ✅ Проверка Facebook по email
- ✅ Проверка Google аккаунта (Gmail)
- ✅ Проверка Instagram
- ✅ Проверка Snapchat
- ✅ Проверка X (Twitter)
- ✅ Автоматическое распознавание данных из текста
- ✅ Поддержка CSV файлов
- ✅ Оценка рисков и вердикт (clean/risky/spam)

## Установка

1. Клонируйте репозиторий или скачайте файлы

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

**Важно:** Проект использует **aiogram 3.x** для работы с Telegram Bot API.

3. Создайте файл `.env` на основе `env.example` и заполните API ключи:
   - `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
   - `ABSTRACT_API_KEY` - ключ от Abstract API (email validation)
   - `IPDATA_API_KEY` - ключ от ipdata.co
   - `NUMVERIFY_API_KEY` - ключ от numverify (apilayer)
   - `RAPIDAPI_KEY` - ключ от RapidAPI
   - Остальные настройки можно оставить по умолчанию

4. (Опционально) Проверьте готовность проекта:
```bash
python check_setup.py
```

5. Запустите бота:
```bash
python main.py
```

## Получение API ключей

1. **Telegram Bot Token**: Создайте бота через [@BotFather](https://t.me/BotFather) в Telegram
2. **Abstract API**: Зарегистрируйтесь на [abstractapi.com](https://www.abstractapi.com/api/email-validation)
3. **ipdata.co**: Зарегистрируйтесь на [ipdata.co](https://ipdata.co/)
4. **numverify**: Зарегистрируйтесь на [apilayer.com](https://apilayer.com/marketplace/numverify-api)
5. **RapidAPI**: Зарегистрируйтесь на [rapidapi.com](https://rapidapi.com/) и подпишитесь на нужные API:
   - WhatsApp Checker
   - Facebook Checker
   - Google Checker
   - Instagram Checker
   - Snapchat Checker
   - X Checker

## Использование

### Команды бота:
- `/start` - Начать работу с ботом
- `/help` - Показать справку

### Форматы ввода данных:

1. **CSV файл**: Загрузите файл с колонками email, ip, phone (или любые другие названия)

2. **Ручной ввод** - отправьте текст в любом формате:
   - `email=test@example.com | ip=192.168.1.1 | phone=+1234567890`
   - `test@example.com 192.168.1.1 +1234567890`
   - Просто текст - бот автоматически распознает email, IP и телефон

### Результаты проверки:

- **clean** - выглядит нормально (score < 50)
- **risky** - есть заметные риски (score 50-74)
- **spam** - очень похоже на спам/мошенничество (score >= 75)

Бот показывает детальную информацию по каждой проверке, включая оценки рисков и причины.
