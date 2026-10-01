# Инструкция по настройке

## Быстрый старт

1. **Установите Python 3.11 или выше**

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Создайте файл `.env`:**
```bash
cp env.example .env
```

4. **Заполните `.env` файл своими API ключами:**
   - Получите токен бота от @BotFather в Telegram
   - Зарегистрируйтесь на всех необходимых сервисах и получите API ключи

5. **Запустите бота:**
```bash
python main.py
```

## Структура проекта

```
Checkerleads/
├── main.py              # Точка входа
├── bot.py               # Telegram бот
├── config.py            # Конфигурация
├── requirements.txt     # Зависимости
├── services/            # Сервисы проверки
│   ├── email_checker.py
│   ├── ip_checker.py
│   ├── phone_checker.py
│   ├── whatsapp_checker.py
│   ├── social_checkers.py
│   └── lead_checker.py
└── utils/               # Утилиты
    ├── data_parser.py
    └── risk_scorer.py
```

## Примечания

- Все проверки выполняются асинхронно для ускорения работы
- Бот автоматически распознает данные из текста
- Поддерживается загрузка CSV файлов
- Результаты форматируются в читаемый вид
