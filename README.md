# Планер-календарь с Telegram-напоминаниями

Теперь приложение работает **без внешних Python-библиотек**: только стандартная библиотека Python.

## Что умеет
- веб-интерфейс для создания и удаления задач;
- хранение задач в SQLite (`planner.db`);
- REST API:
  - `GET /api/tasks`
  - `POST /api/tasks`
  - `DELETE /api/tasks/<id>`
- автоматическая отправка напоминаний в Telegram (поток-планировщик каждые 10 секунд).

## Быстрый старт
```bash
cp .env.example .env
# укажи TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
python3 app.py
```

Открой: `http://localhost:8000`

## Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен бота;
- `TELEGRAM_CHAT_ID` — твой chat_id;
- `APP_HOST` (опционально, по умолчанию `0.0.0.0`);
- `APP_PORT` (опционально, по умолчанию `8000`).

## Как узнать chat_id
1. Напиши боту любое сообщение.
2. Открой:
   `https://api.telegram.org/bot<ТВОЙ_ТОКЕН>/getUpdates`
3. Возьми значение `chat.id`.

## Примечание
Если `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` не заданы, интерфейс и API работают, но отправка в Telegram будет пропускаться с предупреждением в логах.
