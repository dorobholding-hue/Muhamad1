from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import Flask, g, redirect, render_template, request, session, url_for
from passlib.hash import pbkdf2_sha256

from .database import SessionLocal
from .models import User


def load_user(user_id: int) -> Optional[User]:
    with SessionLocal() as db:
        return db.get(User, user_id)


def login_required(view: Callable):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))
        user = load_user(user_id)
        if not user:
            session.clear()
            return redirect(url_for("login"))
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped_view


def authenticate(username: str, password: str) -> Optional[User]:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user and pbkdf2_sha256.verify(password, user.password_hash):
            return user
    return None


def register_default_admin(app: Flask) -> None:
    with SessionLocal() as db:
        if db.query(User).count() == 0:
            from .models import Project

            default_project = Project(name="Default Project")
            db.add(default_project)
            db.flush()
            admin = User(
                username="admin",
                password_hash=pbkdf2_sha256.hash("admin"),
                role="admin",
                project_id=default_project.id,
            )
            db.add(admin)
            db.commit()


def setup_auth_routes(app: Flask) -> None:
    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            user = authenticate(username, password)
            if user:
                session["user_id"] = user.id
                return redirect(url_for("dashboard"))
            error = "Неверный логин или пароль"
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.before_request
    def inject_user():
        user_id = session.get("user_id")
        g.current_user = load_user(user_id) if user_id else None

