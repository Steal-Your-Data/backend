import os
import pytest
from flask import Flask
from flask_cors import CORS
from extentions import db, socketio  # Import your extensions
from routes.session_routes import session_bp
from routes.movie_routes import movie_bp
import werkzeug

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '2.0.0'

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'your_secret_key'
    })
    db.init_app(app)
    app.register_blueprint(session_bp, url_prefix='/session')
    app.register_blueprint(movie_bp, url_prefix='/movies')
    return app

@pytest.fixture
def app_fixture():
    app = create_app()
    with app.app_context():
        db.create_all()
        # Patch socketio.emit to be a no-op during tests.
        socketio.emit = lambda *args, **kwargs: None
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app_fixture):
    return app_fixture.test_client()