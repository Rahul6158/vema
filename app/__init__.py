import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

login_manager = LoginManager()


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', os.path.join(app.instance_path, 'data.db'))

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
