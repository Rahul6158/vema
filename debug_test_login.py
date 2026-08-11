from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    client = app.test_client()
    response = client.post('/login', data={'email': 'admin@example.com', 'password': 'adminpass'}, follow_redirects=False)
    print('POST /login status', response.status_code)
    print('Location', response.headers.get('Location'))
    print('Response data', response.data.decode()[:400])
