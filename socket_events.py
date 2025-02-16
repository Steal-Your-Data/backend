from flask import request
from flask_socketio import join_room
from extentions import socketio  # Import the initialized socketio instance
from model import SessionParticipant,User
@socketio.on('connect')
def handle_connect():
    user_id = request.args.get("user_id")  # Extract user ID from query params
    if user_id:
        join_room(f'notif_{user_id}')  # User joins their personal notification room
        print(f"User {user_id} connected and joined room notif_{user_id}")

        # # Add user to any session they are part of
        # active_sessions = SessionParticipant.query.filter_by(user_id=user_id).all()
        # for session in active_sessions:
        #     join_room(f'session_{session.session_id}')
        #     print(f"User {user_id} joined session room session_{session.session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    print("User disconnected")

@socketio.on('join_session_room')
def handle_join_session_room(data):
    session_id = data.get("session_id")
    user_id = request.args.get("user_id")  # from the socket connection
    if session_id and user_id:
        join_room(f"session_{session_id}")
        print(f"User {user_id} joined session room session_{session_id}")
        # Now broadcast that the user joined:
        user = User.query.get(user_id)
        name = user.username if user else "Unknown"
        socketio.emit("user_joined",
                      {"session_id": session_id, "user_id": user_id, "name": name},
                      room=f"session_{session_id}")
