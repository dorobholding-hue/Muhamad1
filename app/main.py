from __future__ import annotations

from typing import Any

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import select

from .auth import login_required, register_default_admin, setup_auth_routes
from .database import SessionLocal, init_db
from .hikvision import ingest_device_events
from .models import Employee, Project, TimeEntry, User
from .permissions import require_admin, require_project_access
from .time_service import process_terminal_event


def _parse_time(value: str):
    hours, minutes = value.split(":")
    return __import__("datetime").time(int(hours), int(minutes))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    init_db()
    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    setup_auth_routes(app)
    register_default_admin(app)

    @app.route("/")
    @login_required
    def dashboard():
        with SessionLocal() as db:
            projects = db.scalars(select(Project)).all()
            recent_events = (
                db.query(TimeEntry)
                .order_by(TimeEntry.created_at.desc())
                .limit(10)
                .all()
            )
            return render_template("dashboard.html", projects=projects, events=recent_events)

    @app.route("/projects/new", methods=["GET", "POST"])
    @login_required
    @require_admin
    def new_project():
        if request.method == "POST":
            name = request.form.get("name", "")
            timezone = request.form.get("timezone", "UTC")
            start = request.form.get("start", "09:00")
            end = request.form.get("end", "18:00")
            grace = int(request.form.get("grace", "5"))
            project = Project(
                name=name,
                timezone=timezone,
                workday_start=_parse_time(start),
                workday_end=_parse_time(end),
                grace_minutes=grace,
            )
            with SessionLocal() as db:
                db.add(project)
                db.commit()
            flash("Проект создан", "success")
            return redirect(url_for("dashboard"))
        return render_template("project_form.html")

    @app.route("/projects/<int:project_id>/employees")
    @login_required
    @require_project_access
    def employees(project_id: int):
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if not project:
                abort(404)
            return render_template("employees.html", project=project)

    @app.route("/projects/<int:project_id>/employees/new", methods=["GET", "POST"])
    @login_required
    @require_project_access
    def add_employee(project_id: int):
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if not project:
                abort(404)
            if request.method == "POST":
                full_name = request.form.get("full_name", "")
                device_code = request.form.get("device_code", "")
                telegram_handle = request.form.get("telegram_handle")
                employee = Employee(
                    project_id=project.id,
                    full_name=full_name,
                    device_code=device_code,
                    telegram_handle=telegram_handle,
                )
                db.add(employee)
                db.commit()
                flash("Сотрудник добавлен", "success")
                return redirect(url_for("employees", project_id=project.id))
            return render_template("employee_form.html", project=project)

    @app.route("/time-entries/<int:employee_id>")
    @login_required
    def time_entries(employee_id: int):
        with SessionLocal() as db:
            employee = db.get(Employee, employee_id)
            if not employee:
                abort(404)
            if not g.current_user.has_project_access(employee.project_id):
                abort(403)
            entries = (
                db.query(TimeEntry)
                .filter(TimeEntry.employee_id == employee_id)
                .order_by(TimeEntry.work_date.desc())
                .all()
            )
            return render_template("time_entries.html", employee=employee, entries=entries)

    @app.route("/users/new", methods=["GET", "POST"])
    @login_required
    @require_admin
    def add_user():
        with SessionLocal() as db:
            projects = db.scalars(select(Project)).all()
            if request.method == "POST":
                from passlib.hash import pbkdf2_sha256

                username = request.form.get("username", "")
                password = request.form.get("password", "")
                role = request.form.get("role", "hr")
                project_id = request.form.get("project_id")
                project_id_value = int(project_id) if project_id else None
                user = User(
                    username=username,
                    password_hash=pbkdf2_sha256.hash(password),
                    role=role,
                    project_id=project_id_value,
                )
                db.add(user)
                db.commit()
                flash("Пользователь создан", "success")
                return redirect(url_for("dashboard"))
            return render_template("user_form.html", projects=projects)

    @app.route("/api/hikvision/events", methods=["POST"])
    def hikvision_events():
        payload: list[dict[str, Any]] = request.get_json(force=True, silent=True) or []
        with SessionLocal() as db:
            events = ingest_device_events(db, payload)
        return {"saved": len(events)}

    @app.route("/api/manual-check", methods=["POST"])
    @login_required
    def manual_check():
        employee_id = int(request.form.get("employee_id", 0))
        direction = request.form.get("direction", "in")
        timestamp = request.form.get("timestamp")
        with SessionLocal() as db:
            employee = db.get(Employee, employee_id)
            if not employee:
                abort(404)
            if not g.current_user.has_project_access(employee.project_id):
                abort(403)
            process_terminal_event(db, employee, timestamp, direction)
        flash("Отметка сохранена", "success")
        return redirect(url_for("time_entries", employee_id=employee_id))


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
