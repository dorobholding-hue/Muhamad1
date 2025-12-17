from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort, g


def require_admin(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user or not user.has_admin_access():
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def require_project_access(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = getattr(g, "current_user", None)
        project_id = kwargs.get("project_id")
        if not user or project_id is None or not user.has_project_access(int(project_id)):
            abort(403)
        return view(*args, **kwargs)

    return wrapper

