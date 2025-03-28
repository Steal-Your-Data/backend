from flask import Blueprint, request, jsonify
from extentions import db, socketio
from model import Session, SessionParticipant, MoviePocket
from sqlalchemy.sql import func
import random

session_bp = Blueprint('session', __name__)

def generate_unique_session_id():
    while True:
        new_id = str(random.randint(100000, 999999))  # Generate a 6-digit ID
        existing_session = Session.query.get(new_id)  # Check if it already exists
        if not existing_session:
            return new_id  # Return only if it's unique

# Start a New Session and Invite Friends
@session_bp.route('/start', methods=['POST'])
def start_session():
    data = request.json
    host_name = data.get('host_name')

    if not host_name:
        return jsonify({'error': 'host_name is required'}), 400

    new_session = Session(id=generate_unique_session_id(), host_name=host_name, status='pending')
    print(new_session.id)
    db.session.add(new_session)
    db.session.commit()

    # Add host as participant
    host_participant = SessionParticipant(session_id=new_session.id, name=host_name)
    db.session.add(host_participant)
    db.session.commit()

    socketio.emit('message', {'session_id': new_session.id, 'name': host_name}, room=f'session_{new_session.id}')

    return jsonify({'message': 'Session started', 'session_id': new_session.id, 'participant_id': host_participant.id})


@session_bp.route('/join', methods=['POST'])
def join_session():
    data = request.json
    session_id = data.get('session_id')
    join_name = data.get('name')

    if not session_id or not join_name:
        return jsonify({'error': 'Both session_id and name are required'}), 400

    session = Session.query.filter_by(id=session_id).first()

    if not session:
        return jsonify({'error': 'Session does not exist'}), 404

    start = session.status
    if start == 'active':
        return jsonify({'message': 'Session has already started, no way for joining'})
    elif start == 'completed':
        return jsonify({'message': 'Session has already finished, no way for joining'})
    else:
        new_session_participant = SessionParticipant(session_id=session_id, name=join_name)
        db.session.add(new_session_participant)
        db.session.commit()

        # socketio.emit('message', {'session_id': session_id, 'name': join_name}, room=f'session_{session_id}')
        return jsonify({'message': 'Join session successfully', 'participant_ID': new_session_participant.id})


@session_bp.route('/begin', methods=['POST'])
def Begin():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400
    session = Session.query.filter_by(id=session_id).first()
    if not session:
        return jsonify({'error': 'Session does not exist'}), 404

    session.status = 'active'
    db.session.commit()
    socketio.emit('session_begin', {'session_id': session_id}, room=f'session_{session_id}')
    return jsonify({'message': f'session {session_id} start'})


@session_bp.route('/list_join_participants', methods=['GET'])
def list_participants():
    session_id = request.args.get('session_id')  # Retrieve from query params
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

        # Your logic to fetch participants based on session_id
    participants = SessionParticipant.query.filter_by(session_id=session_id)  # Example function
    participants_name = []
    for elem in participants:
        participants_name.append(elem.name)

    return jsonify({'session_id': session_id, 'participants_name': participants_name})


@session_bp.route('/add_movie', methods=['POST'])
def add_movie():
    data = request.json
    session_id = data.get('session_id')
    movie_id = data.get('movie_id')
    p_id = data.get('participant_ID')

    # Check for missing required parameters
    if not all([session_id, movie_id, p_id]):
        return jsonify({'error': 'Missing session_id, movie_id, or participant_ID'}), 400

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(id=p_id).first()
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
def finish_selection():
    data = request.json
    session_id = data.get('session_id')
    p_id = data.get('participant_id')

    # Validate required parameters
    if not session_id or not p_id:
        return jsonify({'error': 'Missing session_id or participant_id'}), 400

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(id=p_id).first()
    # print(participant.session_id == session_id)
    # print(type(session_id))
    # print(type(participant.session_id))
    if not participant or str(participant.session_id) != str(session_id):
        return jsonify({'message': 'Not part of this session'}), 403

    # Mark this user as done selecting movies
    participant.done_selecting = True
    db.session.commit()

    # Retrieve all participants in the session
    all_participants = SessionParticipant.query.filter_by(session_id=session_id).all()
    total_participants = len(all_participants)
    done_participants = sum(1 for p in all_participants if p.done_selecting)

    # Emit progress update to all participants
    socketio.emit('selection_progress', {
        'session_id': session_id,
        'total_participants': total_participants,
        'done_participants': done_participants
    }, room=f'session_{session_id}')

    # Check if all participants are done selecting
    if done_participants == total_participants:
        socketio.emit('selection_complete', {'session_id': session_id}, room=f'session_{session_id}')

        '''do not capture this'''
        return jsonify({
            'message': f'All users finished selecting for session {session_id}. Voting can start now.',
            'total_participants': total_participants,
            'done_participants': done_participants
        })

    return jsonify({
        'message': 'You have finished selecting. Waiting for others.',
        'total_participants': total_participants,
        'done_participants': done_participants
    })


@session_bp.route('/movies_in_pocket', methods=['GET'])
def movies_in_pocket():
    p_id = request.args.get('participant_id')  # Use request.args for query parameters
    session_id = request.args.get('session_id')

    if not p_id or not session_id:
        return jsonify({'message': 'Missing session_id or participant_id'}), 400

    # Check if the user is a participant in this session
    participant = SessionParticipant.query.filter_by(session_id=session_id, id=p_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    # Retrieve unique movies in the session's movie pocket
    unique_movies = (
        db.session.query(MoviePocket.movie_id, func.min(MoviePocket.votes))
        .filter(MoviePocket.session_id == session_id)
        .group_by(MoviePocket.movie_id)
        .all()
    )

    # Prepare response
    movie_list = [{'movie_id': movie_id, 'votes': votes} for movie_id, votes in unique_movies]

    return jsonify({'session_id': session_id, 'movies': movie_list})


@session_bp.route('/vote', methods=['POST'])
def vote():
    data = request.json
    session_id = data.get('session_id')
    movie_id = data.get('movie_id')
    p_id = data.get('participant_id')

    # Validate all required parameters
    if not session_id or not movie_id or not p_id:
        return jsonify({'error': 'Missing session_id, movie_id, or participant_id'}), 400

    participant = SessionParticipant.query.filter_by(session_id=session_id, id=p_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

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
def finish_voting():
    data = request.json
    session_id = data.get('session_id')
    p_id = data.get('participant_id')

    # Validate all required parameters
    if not session_id or not p_id:
        return jsonify({'error': 'Missing session_id, or participant_id'}), 400

    # Check if the user is a participant in this session
    participant = SessionParticipant.query.filter_by(id=p_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    # Mark this user as done voting
    participant.done_voting = True
    db.session.commit()


    # Retrieve all participants in the session
    all_participants = SessionParticipant.query.filter_by(session_id=session_id).all()
    total_participants = len(all_participants)
    done_participants = sum(1 for p in all_participants if p.done_voting)

    # Emit progress update to all participants
    socketio.emit('voting_progress', {
        'session_id': session_id,
        'total_participants': total_participants,
        'done_participants': done_participants
    }, room=f'session_{session_id}')

    # Check if all participants are done selecting
    if done_participants == total_participants:
        socketio.emit('voting_complete', {'session_id': session_id}, room=f'session_{session_id}')

        '''do not capture this'''
        return jsonify({
            'message': f'All users finished voting for session {session_id}.',
            'total_participants': total_participants,
            'done_participants': done_participants
        })

    return jsonify({
        'message': 'You have finished voting. Waiting for others.',
        'total_participants': total_participants,
        'done_participants': done_participants
    })

# Retrieve the Final (Winning) Movie for the Session
@session_bp.route('/final_movie/<string:session_id>', methods=['GET'])
def final_movie(session_id):
    winning_movie = MoviePocket.query.filter_by(session_id=session_id).order_by(MoviePocket.votes.desc()).first()

    if not winning_movie:
        return jsonify({'message': 'No movie selected'}), 404

    # Emit the winning movie to all session participants
    socketio.emit('final_movie_result',
                  {'session_id': session_id, 'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes},
                  room=f'session_{session_id}')

    return jsonify({'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes})
