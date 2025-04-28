# Используем официальный Python образ
FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry (опционально, если понадобится) или pip обновляем
RUN pip install --upgrade pip

# Копируем requirements внутрь контейнера
COPY requirements.txt /app/requirements.txt

# Переходим в рабочую директорию
WORKDIR /app

# Устанавливаем все зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение внутрь контейнера
COPY . /app

ENV PYTHONPATH=/app
# Команда по умолчанию для запуска приложения
CMD ["python", "voice_bot/app.py"]