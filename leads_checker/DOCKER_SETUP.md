# Инструкция по запуску бота через Docker

## Быстрый старт

### 1. Подготовка

Убедитесь, что у вас есть файл `.env` с необходимыми API ключами:
```env
TELEGRAM_BOT_TOKEN=your_token_here
ABSTRACT_API_KEY=your_key_here
IPDATA_API_KEY=your_key_here
NUMVERIFY_API_KEY=your_key_here
RAPIDAPI_KEY=your_key_here
```

### 2. Запуск через Docker Compose (рекомендуется)

```bash
# Запустить бота
docker-compose up -d

# Посмотреть логи
docker-compose logs -f

# Остановить бота
docker-compose down

# Перезапустить бота
docker-compose restart
```

### 3. Запуск через Docker напрямую

```bash
# Собрать образ
docker build -t checkerleads-bot .

# Запустить контейнер
docker run -d \
  --name checkerleads-bot \
  --restart unless-stopped \
  --env-file .env \
  checkerleads-bot

# Посмотреть логи
docker logs -f checkerleads-bot

# Остановить контейнер
docker stop checkerleads-bot

# Удалить контейнер
docker rm checkerleads-bot
```

## Управление

### Просмотр логов
```bash
# Docker Compose
docker-compose logs -f checkerleads-bot

# Docker
docker logs -f checkerleads-bot
```

### Перезапуск после изменений
```bash
# Пересобрать и перезапустить (ОБЯЗАТЕЛЬНО при изменении кода!)
docker-compose up -d --build

# Или пересобрать без кэша (если есть проблемы)
docker-compose build --no-cache
docker-compose up -d

# Или просто перезапустить (если код не менялся)
docker-compose restart
```

### Обновление .env файла
После изменения `.env` файла:
```bash
docker-compose restart
```

## Проверка работы

После запуска проверьте логи:
```bash
docker-compose logs -f
```

Вы должны увидеть:
```
✅ Бот успешно запущен! Ожидаю сообщений...
```

## Troubleshooting

### Бот не запускается
1. Проверьте, что `.env` файл существует и содержит все необходимые ключи
2. Проверьте логи: `docker-compose logs`

### Ошибки подключения к API
1. Убедитесь, что все API ключи в `.env` правильные
2. Проверьте интернет-соединение контейнера

### Контейнер постоянно перезапускается
1. Проверьте логи: `docker-compose logs`
2. Убедитесь, что все зависимости установлены правильно
