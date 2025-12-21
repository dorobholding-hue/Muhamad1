from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./timekeeper.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, future=True, echo=False
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_employee_face_column()
    _ensure_settings_table()


def _ensure_employee_face_column() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("PRAGMA table_info(employees)"))
        columns = {row[1] for row in result}
        if "face_image_path" not in columns:
            connection.execute(text("ALTER TABLE employees ADD COLUMN face_image_path VARCHAR(255)"))
            connection.commit()


def _ensure_settings_table() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        )
        if not result.first():
            connection.execute(
                text(
                    """
                    CREATE TABLE settings (
                        id INTEGER PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value VARCHAR(255) NOT NULL
                    )
                    """
                )
            )
            connection.commit()
