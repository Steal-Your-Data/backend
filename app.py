from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'  # Change for production
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")  # Enables real-time WebSocket updates

# Import Blueprints
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.session_routes import session_bp
from routes.movie_routes import movie_bp

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(session_bp, url_prefix='/session')
app.register_blueprint(movie_bp, url_prefix='/movies')

if __name__ == '__main__':
    socketio.run(app, debug=True)
