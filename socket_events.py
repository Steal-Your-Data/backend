from flask import request
from flask_socketio import join_room
from extentions import socketio  # Import the initialized socketio instance

@socketio.on('connect')
def handle_connect():
    user_id = request.args.get("user_id")  # Extract user ID from query params
    if user_id:
        join_room(f'notif_{user_id}')  # User joins their personal notification room
        print(f"User {user_id} connected and joined room notif_{user_id}")

@socketio.on('disconnect')
def handle_disconnect():
    print("User disconnected")
