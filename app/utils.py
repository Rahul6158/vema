from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if not current_user.role or current_user.role.name != role_name:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
