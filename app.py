import json
import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BUNDLE_DIR = _bundle_dir()
RUNTIME_DIR = _runtime_dir()
DB_PATH = RUNTIME_DIR / "planner.db"
STATIC_DIR = BUNDLE_DIR / "static"
TEMPLATE_DIR = BUNDLE_DIR / "templates"


def load_env_file() -> None:
    env_path = RUNTIME_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_at_utc TEXT NOT NULL,
                reminded INTEGER NOT NULL DEFAULT 0,
                created_at_utc TEXT NOT NULL
            )
            """
        )


def parse_iso_utc(value: str) -> datetime:
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def send_telegram_message(text: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("[WARN] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID не заданы, отправка пропущена")
        return False

    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = Request(
        url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                body = response.read().decode("utf-8", errors="replace")
                print(f"[WARN] Telegram API error: {response.status} {body}")
                return False
            return True
    except Exception as exc:
        print(f"[WARN] Telegram отправка не удалась: {exc}")
        return False


def process_due_tasks() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, description, due_at_utc
            FROM tasks
            WHERE reminded = 0 AND due_at_utc <= ?
            ORDER BY due_at_utc ASC
            """,
            (now,),
        ).fetchall()

        for row in rows:
            text = (
                f"⏰ Напоминание: {row['title']}\n"
                f"Когда: {row['due_at_utc']} UTC\n"
                f"Описание: {row['description'] or '-'}"
            )
            if send_telegram_message(text):
                conn.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (row["id"],))


def scheduler_loop(stop_event: threading.Event, interval_seconds: int = 10) -> None:
    while not stop_event.is_set():
        process_due_tasks()
        stop_event.wait(interval_seconds)


class PlannerHandler(BaseHTTPRequestHandler):
    server_version = "PlannerHTTP/1.0"

    def _json_response(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parse_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            obj = json.loads(raw.decode("utf-8"))
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._send_file(TEMPLATE_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/static/app.js":
            return self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/static/styles.css":
            return self._send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
        if parsed.path == "/api/tasks":
            with db_connection() as conn:
                rows = conn.execute(
                    "SELECT id, title, description, due_at_utc, reminded FROM tasks ORDER BY due_at_utc ASC"
                ).fetchall()
            return self._json_response([dict(row) for row in rows])
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/tasks":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        data = self._parse_json_body()
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        due_at = data.get("due_at")

        if not title:
            return self._json_response({"error": "title is required"}, HTTPStatus.BAD_REQUEST)
        if not due_at:
            return self._json_response({"error": "due_at is required"}, HTTPStatus.BAD_REQUEST)

        try:
            due_at_utc = parse_iso_utc(due_at).isoformat()
        except ValueError:
            return self._json_response({"error": "due_at must be valid ISO datetime"}, HTTPStatus.BAD_REQUEST)

        created_at = datetime.now(timezone.utc).isoformat()
        with db_connection() as conn:
            cur = conn.execute(
                "INSERT INTO tasks(title, description, due_at_utc, created_at_utc) VALUES (?, ?, ?, ?)",
                (title, description, due_at_utc, created_at),
            )
            new_id = cur.lastrowid

        return self._json_response(
            {
                "id": new_id,
                "title": title,
                "description": description,
                "due_at_utc": due_at_utc,
                "reminded": 0,
            },
            HTTPStatus.CREATED,
        )

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        prefix = "/api/tasks/"
        if not parsed.path.startswith(prefix):
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        task_id_str = parsed.path[len(prefix) :]
        if not task_id_str.isdigit():
            return self._json_response({"error": "invalid id"}, HTTPStatus.BAD_REQUEST)

        with db_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (int(task_id_str),))

        return self._json_response({"ok": True})


def run() -> None:
    load_env_file()
    init_db()

    stop_event = threading.Event()
    scheduler = threading.Thread(target=scheduler_loop, args=(stop_event,), daemon=True)
    scheduler.start()

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), PlannerHandler)

    print(f"Planner запущен: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()


if __name__ == "__main__":
    run()
