# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager()
socketio = SocketIO()
