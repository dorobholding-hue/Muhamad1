from __future__ import annotations

import datetime as dt
import pytz
from sqlalchemy.orm import Session

from .models import Employee, Project, TerminalEvent, TimeEntry
from .telegram_bot import notify_late


def localized_timestamp(project: Project, timestamp: str | dt.datetime) -> dt.datetime:
    if isinstance(timestamp, str):
        naive_dt = dt.datetime.fromisoformat(timestamp)
    else:
        naive_dt = timestamp
    tz = pytz.timezone(project.timezone or "UTC")
    if naive_dt.tzinfo is None:
        naive_dt = tz.localize(naive_dt)
    return naive_dt.astimezone(tz)


def process_terminal_event(
    db_session: Session,
    employee: Employee,
    timestamp: str | dt.datetime,
    direction: str,
    raw_payload: str | None = None,
) -> TerminalEvent:
    project = employee.project
    localized_ts = localized_timestamp(project, timestamp)
    terminal_event = TerminalEvent(
        employee_id=employee.id,
        timestamp=localized_ts,
        direction=direction,
        raw_payload=raw_payload,
    )
    db_session.add(terminal_event)

    work_date = localized_ts.date()
    entry = (
        db_session.query(TimeEntry)
        .filter(TimeEntry.employee_id == employee.id, TimeEntry.work_date == work_date)
        .first()
    )
    if not entry:
        entry = TimeEntry(employee_id=employee.id, work_date=work_date)
        db_session.add(entry)

    if direction == "in" and (not entry.first_check_in or localized_ts < entry.first_check_in):
        entry.first_check_in = localized_ts
        mark_lateness(entry, project, employee)
    elif direction == "out":
        entry.last_check_out = localized_ts

    db_session.commit()
    return terminal_event


def mark_lateness(entry: TimeEntry, project: Project, employee: Employee) -> None:
    start_dt = dt.datetime.combine(entry.work_date, project.workday_start)
    grace_delta = dt.timedelta(minutes=project.grace_minutes)
    start_with_grace = start_dt + grace_delta
    employee_check_in = entry.first_check_in
    if not employee_check_in:
        return
    tz = pytz.timezone(project.timezone or "UTC")
    localized_start = tz.localize(start_with_grace)
    if employee_check_in > localized_start:
        delta = employee_check_in - localized_start
        entry.is_late = True
        notify_late(employee.full_name, project.name, int(delta.total_seconds() // 60))
    else:
        entry.is_late = False

