from flask import Flask

from .database import init_db
from .main import register_routes


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    init_db()
    register_routes(app)
    return app
