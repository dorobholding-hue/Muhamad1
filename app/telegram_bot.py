from __future__ import annotations

import os
import time
from typing import Optional

import requests

from .database import SessionLocal
from .models import Setting

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"


def send_message(text: str, chat_id: Optional[str] = None) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    destination = chat_id or os.getenv("TELEGRAM_CHAT_ID") or get_saved_chat_id()
    if not token or not destination:
        return
    url = API_URL.format(token=token)
    payload = {"chat_id": destination, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)


def notify_late(employee_name: str, project_name: str, minutes_late: int) -> None:
    message = (
        f"⏰ Сотрудник <b>{employee_name}</b> опоздал на {minutes_late} мин. "
        f"Проект: {project_name}."
    )
    send_message(message)


def save_chat_id(chat_id: str) -> None:
    with SessionLocal() as db:
        setting = db.query(Setting).filter(Setting.key == "telegram_chat_id").first()
        if setting:
            setting.value = chat_id
        else:
            setting = Setting(key="telegram_chat_id", value=chat_id)
            db.add(setting)
        db.commit()


def get_saved_chat_id() -> Optional[str]:
    with SessionLocal() as db:
        setting = db.query(Setting).filter(Setting.key == "telegram_chat_id").first()
        return setting.value if setting else None


def run_polling() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    offset = 0
    while True:
        response = requests.get(
            UPDATES_URL.format(token=token),
            params={"timeout": 30, "offset": offset},
            timeout=35,
        )
        response.raise_for_status()
        data = response.json()
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            chat_id = message.get("chat", {}).get("id")
            if not chat_id:
                continue
            if text in {"/start", "/setchat"}:
                save_chat_id(str(chat_id))
                send_message("✅ Чат сохранён для уведомлений.", str(chat_id))
        time.sleep(1)


if __name__ == "__main__":
    run_polling()
