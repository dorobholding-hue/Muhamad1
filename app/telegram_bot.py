from __future__ import annotations

import os
from typing import Optional

import requests

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str, chat_id: Optional[str] = None) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    destination = chat_id or os.getenv("TELEGRAM_CHAT_ID")
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

