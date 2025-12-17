from __future__ import annotations

import json
import os
from typing import Iterable

import requests

from .models import Employee, TerminalEvent
from .time_service import process_terminal_event


class HikvisionClient:
    """Simplified client for DS-K1T341AM terminals.

    In production you would use the device SDK or ISAPI endpoints. The helper
    below demonstrates how to poll the device for events using the ISAPI
    system/event API. Credentials and host are pulled from environment
    variables for safety.
    """

    def __init__(self) -> None:
        self.host = os.getenv("HIKVISION_HOST", "")
        self.username = os.getenv("HIKVISION_USER", "")
        self.password = os.getenv("HIKVISION_PASSWORD", "")

    def fetch_events(self) -> list[dict]:
        if not self.host or not self.username or not self.password:
            return []
        url = f"https://{self.host}/ISAPI/Event/notification/alertStream"
        try:
            response = requests.get(url, auth=(self.username, self.password), timeout=5, verify=False)
            response.raise_for_status()
            return json.loads(response.text).get("events", [])
        except Exception:
            return []


def ingest_device_events(db_session, payload: Iterable[dict]) -> list[TerminalEvent]:
    ingested: list[TerminalEvent] = []
    for event in payload:
        employee_code = str(event.get("employeeCode"))
        direction = event.get("direction", "in")
        timestamp = event.get("timestamp")
        if not employee_code or not timestamp:
            continue
        employee = (
            db_session.query(Employee)
            .filter(Employee.device_code == employee_code)
            .first()
        )
        if not employee:
            continue
        saved_event = process_terminal_event(
            db_session=db_session,
            employee=employee,
            timestamp=timestamp,
            direction=direction,
            raw_payload=json.dumps(event),
        )
        ingested.append(saved_event)
    return ingested

