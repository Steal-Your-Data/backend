# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

'''
    extentions.py
    
    This file initializes and provides shared Flask extensions for the app:
    - SQLAlchemy (db) for database interactions
    - SocketIO (socketio) for real-time WebSocket communication
'''

db = SQLAlchemy()
socketio = SocketIO()
