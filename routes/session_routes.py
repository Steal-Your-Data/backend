from flask import Blueprint, request, jsonify
from extentions import db, socketio
from model import Session, SessionParticipant, MoviePocket, User
from flask_jwt_extended import jwt_required, get_jwt_identity
session_bp = Blueprint('session', __name__)


# Start a New Session and Invite Friends
@session_bp.route('/start', methods=['POST'])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    data = request.json
    invited_friends = data.get('friends', [])  # List of friend IDs

    new_session = Session(host_id=user_id, status='pending')
    db.session.add(new_session)
    db.session.commit()

    name = User.query.filter_by(id = int(user_id)).first().username

    # Add host as participant
    host_participant = SessionParticipant(session_id=new_session.id, user_id=user_id)
    db.session.add(host_participant)

    # join_room(f'session_{new_session.id}')
    # print(f"User {user_id} joined session room session_{new_session.id}")

    # Add invited friends as participants
    for friend_id in invited_friends:
        participant = SessionParticipant(session_id=new_session.id, user_id=friend_id)
        db.session.add(participant)

    # Notify invited friends
    for friend_id in invited_friends:
        socketio.emit('session_invite',
                      {'session_id': new_session.id, 'host': user_id,'name':name},
                      room=f'notif_{friend_id}')

    db.session.commit()

    return jsonify({'message': 'Session started', 'session_id': new_session.id})


# Respond to a Session Invitation (Accept or Reject)
@session_bp.route('/respond_invite', methods=['POST'])
@jwt_required()
def respond_invite():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')
    action = data.get('action')  # "accept" or "reject"

    name = User.query.filter_by(id=int(user_id)).first().username

    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=int(user_id)).first()
    if not participant:
        return jsonify({'message': 'Session invitation not found'}), 404

    if action == "accept":

        # 2) Then emit "user_joined" to that room
        socketio.emit('user_joined',
                      {'session_id': session_id, 'user_id': user_id, 'name': name},
                      room=f'session_{session_id}')
        return jsonify({'message': 'Joined session successfully'})

    elif action == "reject":
        db.session.delete(participant)
        db.session.commit()
        return jsonify({'message': 'Session invite rejected'})
    else:
        return jsonify({'message': 'Invalid action'}), 400


# Add a Movie to the Session Pocket
@session_bp.route('/add_movie', methods=['POST'])
@jwt_required()
def add_movie():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')
    movie_id = data.get('movie_id')

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    movie_pocket = MoviePocket(session_id=session_id, movie_id=movie_id)
    db.session.add(movie_pocket)
    db.session.commit()

    socketio.emit('movie_added',
                  {'session_id': session_id, 'movie_id': movie_id},
                  room=f'session_{session_id}')
    return jsonify({'message': 'Movie added to pocket'})


# Vote for a Movie in the Session
@session_bp.route('/vote', methods=['POST'])
@jwt_required()
def vote():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')
    movie_id = data.get('movie_id')

    movie_pocket = MoviePocket.query.filter_by(session_id=session_id, movie_id=movie_id).first()
    if not movie_pocket:
        return jsonify({'message': 'Movie not found in pocket'}), 404

    movie_pocket.votes += 1
    db.session.commit()

    socketio.emit('vote_update',
                  {'session_id': session_id, 'movie_id': movie_id, 'votes': movie_pocket.votes},
                  room=f'session_{session_id}')
    return jsonify({'message': 'Vote recorded'})


# Retrieve the Final (Winning) Movie for the Session
@session_bp.route('/final_movie/<int:session_id>', methods=['GET'])
@jwt_required()
def final_movie(session_id):
    winning_movie = MoviePocket.query.filter_by(session_id=session_id).order_by(MoviePocket.votes.desc()).first()
    if not winning_movie:
        return jsonify({'message': 'No movie selected'}), 404
    return jsonify({'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes})
