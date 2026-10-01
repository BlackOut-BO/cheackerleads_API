FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения (включая все поддиректории)
COPY utils/ ./utils/
COPY services/ ./services/
COPY config.py main.py bot.py ./

# Создаем директорию для логов (если нужно)
RUN mkdir -p /app/logs

# Указываем команду запуска
CMD ["python", "main.py"]
