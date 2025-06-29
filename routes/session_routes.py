from collections import defaultdict

import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_socketio import leave_room

from extentions import db, socketio
from model import Session, SessionParticipant, MoviePocket, Movie
from sqlalchemy.sql import func
import random
import hashlib
from routes.Config import TMDB_api

'''
    session_routes.py
    
    This file defines the Flask Blueprint routes for managing movie selection sessions.
    It handles:
    - Starting, joining, and leaving a session
    - Managing session participants
    - Adding and listing movies within a session
    - Facilitating the movie selection and voting phases
    - Determining the final winning movie based on votes
    Socket.IO is used for real-time updates to session participants.
'''

session_bp = Blueprint('session', __name__)

def generate_unique_session_id():
    while True:
        new_id = str(random.randint(100000, 999999))  # Generate a 6-digit ID
        existing_session = Session.query.get(new_id)  # Check if it already exists
        if not existing_session:
            return new_id  # Return only if it's unique

#
# Start a new movie session and invite the host as the first participant
#
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


#
# Join an existing session if it has not started or completed
#
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
        return jsonify({'error': 'Session has already started, no way for joining'})
    elif start == 'completed':
        return jsonify({'error': 'Session has already finished, no way for joining'})
    else:

        existing_names = [p.name for p in SessionParticipant.query.filter_by(session_id=session_id).all()]
        if join_name in existing_names:
            socketio.emit('name_exists', {'session_id': session_id, 'name': join_name}, room=f'session_{session_id}')
            return jsonify({'error': 'This name is already taken. Please choose another one.'}), 400

        new_session_participant = SessionParticipant(session_id=session_id, name=join_name)
        db.session.add(new_session_participant)
        db.session.commit()

        # socketio.emit('message', {'session_id': session_id, 'name': join_name}, room=f'session_{session_id}')
        return jsonify({'message': 'Join session successfully', 'participant_ID': new_session_participant.id, 'host_name': session.host_name})


#
# Start the movie selection phase of the session
#
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

#
# Leave the session; if the host leaves, the session is disbanded
#
@session_bp.route('/leave', methods=['POST'])
@cross_origin()
def leave_session_http():
    data = request.json
    session_id     = data.get('session_id')
    participant_id = data.get('participant_id')

    if not session_id or not participant_id:
        return jsonify({'error': 'Missing session_id or participant_id'}), 400

    status, payload = remove_participant(session_id, participant_id)   # ← no sid
    return jsonify(payload), status

#
# List all participants in a given session
#
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


#
# Add movies to the session's movie pocket
#
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


#
# Mark a participant as finished selecting movies and check if all are done
#
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


#
# List all unique movies currently in the session's movie pocket
#
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


#
# Vote for a movie in the session's movie pocket
#
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


#
# Mark a participant as finished voting and check if all are done
#
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

#
# Determine the final winning movie based on votes
#
@session_bp.route('/final_movie', methods=['POST'])
@cross_origin()
def final_movie():
    data = request.json
    session_id = data.get('session_id')

    max_votes = (db.session
                 .query(func.max(MoviePocket.votes))
                 .filter(MoviePocket.session_id == session_id)
                 .scalar())
    if max_votes is None:
        return jsonify({'message': 'No movie selected'}), 404

    top_movies = (MoviePocket.query
                  .filter_by(session_id=session_id, votes=max_votes)
                  .all())

    top_movies = sorted(top_movies, key=lambda p: p.movie_id)
    hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    winning_movie = top_movies[hash_value % len(top_movies)]

    all_pockets = MoviePocket.query.filter_by(session_id=session_id).all()
    vote_map = defaultdict(int)
    for p in all_pockets:
        print(str(p.votes))
        vote_map[p.movie_id] += p.votes

    movies_list = []
    for movie_id, votes in vote_map.items():
        tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            'api_key': TMDB_api,
            'language': 'en-US'
        }

        try:
            response = requests.get(tmdb_url, params=params, timeout=5)
            response.raise_for_status()
            movie = response.json()

            genre_names = [g['name'] for g in movie.get('genres', [])]
            genres_str = '-'.join(genre_names) if genre_names else 'Unknown'

            movie_data = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'genres': genres_str,
                'original_language': movie.get('original_language'),
                'overview': movie.get('overview'),
                'popularity': movie.get('popularity'),
                'release_date': movie.get('release_date'),
                'poster_path': movie.get('poster_path')
            }
        except requests.RequestException as exc:
            movie_data = {'id': movie_id}
            print(f"Error fetching movie details: {exc}")

        movies_list.append({'movie': movie_data, 'votes': votes})

    socketio.emit(
        'final_movie_result',
        {
            'session_id': session_id,
            'movie_id': winning_movie.movie_id,
            'votes': winning_movie.votes
        },
        room=f'session_{session_id}'
    )

    return jsonify({
        'movie_id': winning_movie.movie_id,
        'votes': winning_movie.votes,
        'movies_list': movies_list,
    })



def remove_participant(session_id: str, participant_id: int, *, sid: str | None = None
                       ) -> tuple[int, dict]:
    # ── 1. Look-ups ───────────────────────────────────────────────────────────
    session = Session.query.get(session_id)
    if not session:
        return 404, {'error': 'Session does not exist'}

    participant = SessionParticipant.query.filter_by(
        id=participant_id, session_id=session_id
    ).first()
    if not participant:
        return 404, {'error': 'Participant not found in this session'}

    # Keep track if we’re removing today’s host
    is_current_host = (participant.name == session.host_name)

    # ── 2. Remove the user ────────────────────────────────────────────────────
    db.session.delete(participant)
    db.session.commit()          # commit early – the row is gone

    # Pop them out of the Socket.IO room if we know their sid
    if sid:
        leave_room(f'session_{session_id}', sid=sid)

    # Notify clients that someone left
    socketio.emit('participant_left',
                  {'session_id': session_id,
                   'participant_id': participant_id,
                   'participant_name': participant.name},
                  room=f'session_{session_id}')

    # ── 3. Are there still people inside? ─────────────────────────────────────
    remaining = SessionParticipant.query.filter_by(session_id=session_id).all()
    if not remaining:                       # nobody → tear the session down
        db.session.delete(session)
        db.session.commit()
        return 200, {'message': 'Last participant left – session removed'}

    # ── 4. Re-assign host if necessary ───────────────────────────────────────
    if is_current_host:
        new_host = remaining[0]             # “first” remaining user
        session.host_name = new_host.name
        db.session.commit()

        socketio.emit('host_changed',
                      {'session_id': session_id,
                       'new_host_id': new_host.id,
                       'new_host_name': new_host.name},
                      room=f'session_{session_id}')

    # ── 5. Recalculate selection / voting progress ───────────────────────────
    total_participants = len(remaining)
    done_selecting = sum(1 for p in remaining if p.done_selecting)
    done_voting    = sum(1 for p in remaining if p.done_voting)

    # ---- selection progress --------------------------------------------------
    socketio.emit('selection_progress',
                  {'session_id': session_id,
                   'total_participants': total_participants,
                   'done_participants': done_selecting},
                  room=f'session_{session_id}')

    if done_voting == total_participants:
        socketio.emit('voting_complete',
                      {'session_id': session_id},
                      room=f'session_{session_id}')
        return 200, {'message': 'You have left the session'}

    if done_selecting == total_participants:
        movies_in_room = MoviePocket.query.filter_by(session_id=session_id).count()
        if movies_in_room == 0:
            session.status = 'completed'
            db.session.commit()
            socketio.emit('No_Movies',
                          {'session_id': session_id},
                          room=f'session_{session_id}')
        else:
            socketio.emit('selection_complete',
                          {'session_id': session_id},
                          room=f'session_{session_id}')

    # ---- voting progress -----------------------------------------------------
    socketio.emit('voting_progress',
                  {'session_id': session_id,
                   'total_participants': total_participants,
                   'done_participants': done_voting},
                  room=f'session_{session_id}')


    return 200, {'message': 'You have left the session'}
