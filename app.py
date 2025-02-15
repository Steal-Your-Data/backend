# app.py
import os
from flask import Flask
from extentions import db, login_manager, jwt, socketio
from datetime import timedelta
from flask import jsonify

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/terry/Desktop/CS506/movies.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

    # Initialize extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Import and register blueprints here (import after app and extensions are set up)
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.session_routes import session_bp
    from routes.movie_routes import movie_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(session_bp, url_prefix='/session')
    app.register_blueprint(movie_bp, url_prefix='/movies')

    from model import User  # Ensure your User model is imported
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from model import RevokedToken


    # Define JWT callbacks here (optional: you can also define these in extentions.py)
    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]  # Get JWT unique ID
        return RevokedToken.is_token_blacklisted(jti)  # Check if token exists in DB

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "message": "Token has been revoked. Please log in again.",
            "error": "token_revoked"
        }), 401


    return app


import socket_events

if __name__ == "__main__":
    app = create_app()
    socketio.run(app, debug=True)
