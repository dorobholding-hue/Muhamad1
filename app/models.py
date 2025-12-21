from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    workday_start: Mapped[dt.time] = mapped_column(Time, default=dt.time(9, 0))
    workday_end: Mapped[dt.time] = mapped_column(Time, default=dt.time(18, 0))
    grace_minutes: Mapped[int] = mapped_column(Integer, default=5)

    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="project")
    users: Mapped[list["User"]] = relationship("User", back_populates="project")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="hr")
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True)

    project: Mapped[Optional[Project]] = relationship("Project", back_populates="users")

    def has_admin_access(self) -> bool:
        return self.role == "admin"

    def has_project_access(self, project_id: int) -> bool:
        return self.has_admin_access() or self.project_id == project_id


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("project_id", "device_code", name="uq_employee_device"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    device_code: Mapped[str] = mapped_column(String(64), nullable=False)
    telegram_handle: Mapped[Optional[str]] = mapped_column(String(120))
    face_image_path: Mapped[Optional[str]] = mapped_column(String(255))

    project: Mapped[Project] = relationship("Project", back_populates="employees")
    time_entries: Mapped[list["TimeEntry"]] = relationship("TimeEntry", back_populates="employee")
    events: Mapped[list["TerminalEvent"]] = relationship("TerminalEvent", back_populates="employee")


class TerminalEvent(Base):
    __tablename__ = "terminal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="in")
    raw_payload: Mapped[Optional[str]] = mapped_column(String)

    employee: Mapped[Employee] = relationship("Employee", back_populates="events")


class TimeEntry(Base):
    __tablename__ = "time_entries"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_employee_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    work_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    first_check_in: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    last_check_out: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="time_entries")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
