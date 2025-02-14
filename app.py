# app.py
import os
from flask import Flask
from extentions import db, login_manager, jwt, socketio

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/terry/Desktop/CS506/movies.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

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

    return app

if __name__ == "__main__":
    app = create_app()
    socketio.run(app, debug=True)
