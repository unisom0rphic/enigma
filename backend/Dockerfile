# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# === ШАГ 1: ТЯЖЕЛЫЕ БИБЛИОТЕКИ (Кэшируется надолго) ===
# Копируем только файл с тяжелыми либами
COPY requirements-heavy.txt .
# Используем кэш, чтобы не качать заново
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-heavy.txt

# === ШАГ 2: ЛЕГКИЕ БИБЛИОТЕКИ (Быстро меняется) ===
# Копируем обычный requirements
COPY requirements.txt .
# Если добавишь email-validator, этот шаг выполнится быстро (секунды)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# === ШАГ 3: КОД ===
COPY . .

RUN mkdir -p /app/data
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]