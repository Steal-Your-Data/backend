from flask import request
from flask_socketio import join_room,leave_room
from extentions import socketio  # Import the initialized socketio instance
from model import SessionParticipant
from routes.session_routes import remove_participant

sid_to_session: dict[str, tuple[str, str]] = {}
sid_to_participant: dict[str, tuple[str, int]] = {}
'''
    socket_events.py
    
    This file defines the Socket.IO event handlers for real-time communication during movie selection sessions.
    It handles:
    - Users joining a session room
    - Users leaving a session room
    - Broadcasting join and leave events to all participants in a session
'''

# Handle a user joining a session room and broadcast the updated participant list
@socketio.on('join_session_room')
def handle_join_session_room(data):
    session_id = data.get("session_id")
    name = data.get("name")

    participants = SessionParticipant.query.filter_by(session_id=session_id)
    names = []
    for participant in participants:
        names.append(participant.name)

    participant = SessionParticipant.query.filter_by(
        session_id=session_id, name=name
    ).first()

    if participant:
        print(f"found participant {participant.id} for session {session_id}")


    if session_id:
        join_room(f"session_{session_id}")
        print(f"User {name} joined session room session_{session_id} with sid {request.sid}")
        sid_to_session[request.sid] = (session_id, name)
        sid_to_participant[request.sid] = (session_id, participant.id)
        # Now broadcast that the user joined:
        socketio.emit("user_joined",
                      {"session_id": session_id, "name": names},
                      room=f"session_{session_id}")


# Handle a user leaving a session room and notify all remaining participants
@socketio.on('leave_session_room')
def handle_leave_session_room(data):
    session_id = data.get("session_id")
    name = data.get("name")
    if session_id:
        leave_room(f"session_{name}")
        print(f"User {name} left session room session_{session_id}")

        # Broadcast that the user left the session room
        socketio.emit("user_left",
                      {"session_id": session_id, "name": name},
                      room=f"session_{session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    entry = sid_to_participant.pop(request.sid, None)

    if entry is None:
        # The socket never joined a session (e.g. landed on homepage then closed)
        print("Socket %s disconnected but never joined a session" % request.sid)
        return

    session_id, participant_id = entry

    status, payload = remove_participant(
        session_id,
        participant_id,
        sid=request.sid
    )

    if status != 200:
        print(f"Failed to remove participant {participant_id} from session {session_id}: {payload}")
