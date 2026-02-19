# Планер-календарь с Telegram-напоминаниями

Приложение работает на стандартной библиотеке Python и имеет веб-интерфейс:
- создание/удаление задач;
- хранение в SQLite (`planner.db`);
- авто-отправка напоминаний в Telegram.

## Локальный запуск (из исходников)
```bash
cp .env.example .env
# укажи TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
python3 app.py
```
Открой: `http://127.0.0.1:8000`

## Сборка исполняемого файла для macOS
Важно: нативный macOS бинарник собирается **только на macOS**.

### Вариант 1 (локально на Mac)
```bash
./build_macos.sh
```
Готовый файл: `dist/tire-planner`.

### Вариант 2 (через GitHub Actions)
В репозитории добавлен workflow `.github/workflows/build-macos.yml`.
Запусти его вручную (`workflow_dispatch`) или пушни тег `v*`.
После выполнения скачай артефакт `tire-planner-macos`.

## Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен бота;
- `TELEGRAM_CHAT_ID` — твой chat_id;
- `APP_HOST` (по умолчанию `127.0.0.1`);
- `APP_PORT` (по умолчанию `8000`).

## Как узнать chat_id
1. Напиши боту любое сообщение.
2. Открой:
   `https://api.telegram.org/bot<ТВОЙ_ТОКЕН>/getUpdates`
3. Возьми значение `chat.id`.

## Примечание
Если `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` не заданы, интерфейс и API работают, но отправка в Telegram пропускается с предупреждением в логах.
