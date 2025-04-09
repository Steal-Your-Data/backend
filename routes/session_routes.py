from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

from extentions import db, socketio
from model import Session, SessionParticipant, MoviePocket, Movie
from sqlalchemy.sql import func
import random
import hashlib

session_bp = Blueprint('session', __name__)

def generate_unique_session_id():
    while True:
        new_id = str(random.randint(100000, 999999))  # Generate a 6-digit ID
        existing_session = Session.query.get(new_id)  # Check if it already exists
        if not existing_session:
            return new_id  # Return only if it's unique

# Start a New Session and Invite Friends
@session_bp.route('/start', methods=['POST'])
@cross_origin()
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
@cross_origin()
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
        return jsonify({'message': 'Join session successfully', 'participant_ID': new_session_participant.id, 'host_name': session.host_name})


@session_bp.route('/begin', methods=['POST'])
@cross_origin()
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
@cross_origin()
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
@cross_origin()
def add_movie():
    data = request.json
    session_id = data.get('session_id')
    movie_ids = data.get('movie_ids')
    p_id = data.get('participant_ID')

    # Check for missing required parameters
    if not all([session_id, movie_ids, p_id]):
        return jsonify({'error': 'Missing session_id, movie_ids, or participant_ID'}), 400

    # Validate that movie_ids is a list
    if not isinstance(movie_ids, list):
        return jsonify({'error': 'movie_ids must be a list'}), 400

    # Check if the user is a participant
    participant = SessionParticipant.query.filter_by(id=p_id).first()
    if not participant:
        return jsonify({'message': 'Not part of this session'}), 403

    for movie_id in movie_ids:
        movie_pocket = MoviePocket(session_id=session_id, movie_id=movie_id)
        db.session.add(movie_pocket)

    db.session.commit()
    socketio.emit('movie_added',
                  {'session_id': session_id, 'movie_ids': movie_ids},
                  room=f'session_{session_id}')
    return jsonify({'message': 'Movies added to pocket'})


@session_bp.route('/finish_selection', methods=['POST'])
@cross_origin()
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
        movies = MoviePocket.query.filter_by(session_id=session_id).all()
        print(movies)
        if len(movies) == 0:
            session = Session.query.filter_by(id=session_id).first()
            session.status = 'completed'
            db.session.commit()
            socketio.emit('No_Movies', {'session_id': session_id}, room=f'session_{session_id}')
        else:
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


@session_bp.route('/movies_in_pocket', methods=['POST'])
@cross_origin()
def movies_in_pocket():
    data = request.json
    session_id = data.get('session_id')
    p_id = data.get('participant_id')

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
@cross_origin()
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
@cross_origin()
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
@session_bp.route('/final_movie', methods=['POST'])
@cross_origin()
def final_movie():
    data = request.json
    session_id = data.get('session_id')

    # Determine the highest vote count in the session
    max_votes = db.session.query(func.max(MoviePocket.votes)).filter(MoviePocket.session_id == session_id).scalar()
    if max_votes is None:
        return jsonify({'message': 'No movie selected'}), 404

    # Retrieve all movies with the top vote count
    top_movies = MoviePocket.query.filter_by(session_id=session_id, votes=max_votes).all()

    # Sort the movies list by a stable attribute
    top_movies = sorted(top_movies, key=lambda x: x.movie_id)

    # Generate a hash, so the random tie breaker is deterministic across diff clients
    hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    winning_movie = top_movies[hash_value % len(top_movies)]

    # Build movies_list using the full movie details
    movies_list = []
    for pocket in top_movies:
        movie_obj = Movie.query.filter_by(id=pocket.movie_id).first()
        if movie_obj:
            movie_data = {
                'id': movie_obj.id,
                'title': movie_obj.title,
                'genres': movie_obj.genres,
                'original_language': movie_obj.original_language,
                'overview': movie_obj.overview,
                'popularity': movie_obj.popularity,
                'release_date': movie_obj.release_date.isoformat() if movie_obj.release_date else None,
                'poster_path': movie_obj.poster_path
            }
        else:
            movie_data = {'id': pocket.movie_id}  # Fallback if movie not found
        movies_list.append({
            'movie': movie_data,
            'votes': pocket.votes
        })

    # Emit the winning movie to session participants
    socketio.emit('final_movie_result',
                  {'session_id': session_id, 'movie_id': winning_movie.movie_id, 'votes': winning_movie.votes},
                  room=f'session_{session_id}')

    # Return the response with movies_list containing full movie data
    return jsonify({
        'movie_id': winning_movie.movie_id,
        'votes': winning_movie.votes,
        'movies_list': movies_list,
    })


