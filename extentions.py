# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask import jsonify


jwt = JWTManager()  # Do NOT pass 'app' here, init inside 'create_app()' in app.py


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        "message": "Token has expired",
        "error": "token_expired"
    }), 401

# Blocklist Check: Deny any blacklisted token
db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager()
socketio = SocketIO()
