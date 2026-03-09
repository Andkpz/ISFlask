FROM python:3.11-slim

# рабочая папка
WORKDIR /app

# копируем зависимости
COPY requirements.txt .

# устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# копируем проект
COPY . .

# порт Flask
EXPOSE 5000

# запуск приложения
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]