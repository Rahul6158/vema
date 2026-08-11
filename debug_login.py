from app.storage import storage
from app.models import User

storage.ensure_data()
users = storage.users
print('USERS:', [(u.email, u.name, u.active) for u in users])
u = storage.find_user_by_email('admin@example.com')
print('ADMIN EXISTS:', bool(u))
if u:
    print('PASSWORD CHECK:', u.check_password('adminpass'))
