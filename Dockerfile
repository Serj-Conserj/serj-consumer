# 1) какой-нибудь официальный образ Python
FROM python:3.9-slim

# 2) создаём рабочую директорию в контейнере
WORKDIR /app

# 3) копируем зависимости и устанавливаем
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4) копируем весь код приложения
COPY . .

# 5) добавляем корень приложения в PYTHONPATH
ENV PYTHONPATH=/app

# 6) по умолчанию запускаем наш consumer как модуль
CMD ["python", "-u", "-m", "queues.main"]
