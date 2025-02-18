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

    name = User.query.filter_by(id=int(user_id)).first().username

    # Add host as participant
    host_participant = SessionParticipant(session_id=new_session.id, user_id=user_id)
    host_participant.confirmed = True
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
                      {'session_id': new_session.id, 'host': user_id, 'name': name},
                      room=f'notif_{friend_id}')

    db.session.commit()

    return jsonify({'message': 'Session started', 'session_id': new_session.id})




'''
V2 need another def start_session() without jwt authentification and socketio.emit()
def start_session_V2() here 

'''


# Respond to a Session Invitation (Accept or Reject)
@session_bp.route('/respond_invite', methods=['POST'])
@jwt_required()
def respond_invite():
    user_id = get_jwt_identity()
    data = request.json
    if not data:
        return jsonify({'message': 'Invalid JSON payload'}), 422

    session_id = data.get('session_id')
    action = data.get('action')  # "accept" or "reject"

    if session_id is None or action is None:
        return jsonify({'message': 'Missing session_id or action'}), 422

    name = User.query.filter_by(id=int(user_id)).first().username

    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=int(user_id)).first()
    if not participant:
        return jsonify({'message': 'Session invitation not found'}), 404

    if action == "accept":
        participant.confirmed = True
        db.session.commit()
        all_participants = SessionParticipant.query.filter_by(session_id=session_id).all()

        # for elem in all_participants:
        #     print(elem.confirmed)

        if all([p.confirmed for p in all_participants]):
            socketio.emit('session_ready', {'session_id': session_id}, room=f'session_{session_id}')
            return jsonify({'message': f'Session {session_id} is ready for movie selection!'})
        return jsonify({'message': 'Joined session successfully'})

    elif action == "reject":
        db.session.delete(participant)
        db.session.commit()
        remaining_participants = SessionParticipant.query.filter_by(session_id=session_id).all()

        # if len(remaining_participants) < 2:
        #     print('dwda')
        #     socketio.emit('session_cancelled', {'session_id': session_id}, room=f'session_{session_id}')

        if all([p.confirmed for p in remaining_participants]):
            socketio.emit('session_ready', {'session_id': session_id}, room=f'session_{session_id}')
            return jsonify({'message': 'Session invite rejected.'})

        return jsonify({'message': 'Session invite rejected.'})

    else:
        return jsonify({'message': 'Invalid action'}), 400


'''
V2 need a function Join_Room() which use session.ID to join the room and use socket handler 
@socketio.on('join_session_room')
def handle_join_session_room(data) call it in the front-end to send the join info and host person catch that info
'''

'''
V1 and V2 also need a function to start selection movies, in this function, function will be called by
the Host, it will delete those who are on the pending list who still not confirmed, and then broadcast that 
the now we start the game, In this case, for V1, the respond_invite() function only need to broadcast who join
the session, no other message will be broadcast to other users.
'''



'''
if use V2, the following function will not need jwt 
token auth probably change the user_id to name since we do not have user

pseudo-code modif
Foe example
@session_bp.route('/add_movie', methods=['POST'])
@jwt_required()
def add_movie():
    data = request.json
    session_id = data.get('session_id')
    movie_id = data.get('movie_id')
    movie_pocket = MoviePocket(session_id=session_id, movie_id=movie_id)
    db.session.add(movie_pocket)
    db.session.commit()
    socketio.emit('movie_added',
        {'session_id': session_id, 'movie_id': movie_id}, room=f'session_{session_id}')
    return jsonify({'message': 'Movie added to pocket'})
'''

# Add a Movie to the Session Pocket
@session_bp.route('/add_movie', methods=['POST'])
@jwt_required()
def add_movie():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')

    '''
    call it multiple times to add more movies
    '''
    movie_id = data.get('movie_id')

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=int(user_id)).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403
    '''
    call it multiple times to add more movies
    '''
    movie_pocket = MoviePocket(session_id=session_id, movie_id=movie_id)
    db.session.add(movie_pocket)
    db.session.commit()
    '''
    Now once a movie is added, it will broadcast to all the user in the session room
    But You can definitely comment out the socketio to make it more secret
    '''
    socketio.emit('movie_added',
                  {'session_id': session_id, 'movie_id': movie_id},
                  room=f'session_{session_id}')
    return jsonify({'message': 'Movie added to pocket'})


@session_bp.route('/finish_selection', methods=['POST'])
@jwt_required()
def finish_selection():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    # Mark this user as done selecting movies
    participant.done_selecting = True
    db.session.commit()

    # Check if all participants are done selecting
    all_participants = SessionParticipant.query.filter_by(session_id=session_id).all()
    if all([p.done_selecting for p in all_participants]):  # If everyone is done
        socketio.emit('selection_complete', {'session_id': session_id}, room=f'session_{session_id}')
        return jsonify({'message': f'All users finished selecting for session {session_id}. Voting can start now.'})

    return jsonify({'message': 'You have finished selecting. Waiting for others.'})


@session_bp.route('/movies_in_pocket', methods=['GET'])
@jwt_required()
def movies_in_pocket():
    user_id = get_jwt_identity()
    session_id = request.args.get('session_id')

    # Check if the user is a participant in this session
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=int(user_id)).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    # Retrieve all movies in the session's movie pocket
    movies = MoviePocket.query.filter_by(session_id=session_id).all()

    movie_list = [
        {'movie_id': movie.movie_id, 'votes': movie.votes} for movie in movies
    ]

    return jsonify({'session_id': session_id, 'movies': movie_list})


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


@session_bp.route('/finish_voting', methods=['POST'])
@jwt_required()
def finish_voting():
    user_id = get_jwt_identity()
    data = request.json
    session_id = data.get('session_id')

    # Check if the user is a participant in this session
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    # Mark this user as done voting
    participant.done_voting = True
    db.session.commit()

    # Check if all participants are done voting
    all_participants = SessionParticipant.query.filter_by(session_id=session_id).all()
    if all([p.done_voting for p in all_participants]):  # If everyone finished voting
        winning_movie = MoviePocket.query.filter_by(session_id=session_id).order_by(MoviePocket.votes.desc()).first()

        socketio.emit('voting_complete', {'session_id': session_id, 'winning_movie_id': winning_movie.movie_id},
                      room=f'session_{session_id}')
        return jsonify({'message': f'All users finished voting for session {session_id}. final_movie is {winning_movie.movie_id}'})

    return jsonify({'message': 'You have finished voting. Waiting for others.'})


# Retrieve the Final (Winning) Movie for the Session
@session_bp.route('/final_movie/<int:session_id>', methods=['GET'])
@jwt_required()
def final_movie(session_id):
    winning_movie = MoviePocket.query.filter_by(session_id=session_id).order_by(MoviePocket.votes.desc()).first()

    if not winning_movie:
        return jsonify({'message': 'No movie selected'}), 404

    # Emit the winning movie to all session participants
    socketio.emit('final_movie_result',
                  {'session_id': session_id, 'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes},
                  room=f'session_{session_id}')

    return jsonify({'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes})
