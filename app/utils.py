from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*role_names):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            user_role = current_user.role.name if current_user.role else 'Staff'
            if user_role != 'Admin' and user_role not in role_names:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator

