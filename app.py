# app.py
import os
from flask import Flask
from extentions import db, socketio
from flask_cors import CORS

'''
    app.py
    
    This file serves as the entry point for the Flask application.
    It handles:
    - Flask app creation and configuration
    - Extension initialization (SQLAlchemy database and Socket.IO)
    - Blueprint registration for session and movie routes
    - Running the app with Socket.IO support
'''


# Factory function to create and configure the Flask app instance
def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('APP_SQL','sqlite:////Users/rsamb/Downloads/backend/movies_v2.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SECRET_KEY'] = 'your_secret_key'

    # Initialize extensions with the app instance
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Import and register blueprints here (import after app and extensions are set up)

    from routes.session_routes import session_bp
    from routes.movie_routes import movie_bp

    app.register_blueprint(session_bp, url_prefix='/session')
    app.register_blueprint(movie_bp, url_prefix='/movies')

    return app

# Import Socket.IO event handlers (must be after app creation)
import socket_events

# Run the app using Socket.IO server
if __name__ == "__main__":
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0')
