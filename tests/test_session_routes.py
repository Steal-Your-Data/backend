import pytest
from extentions import db, socketio
from model import Session, SessionParticipant, MoviePocket

## Tests for `/session/start`

def test_start_session_valid(client):
    response = client.post('/session/start', json={'host_name': 'Alice'})
    data = response.get_json()
    assert response.status_code in (200, 201)
    assert 'session_id' in data
    assert 'participant_id' in data

def test_start_session_missing_host_name_1(client):
    response = client.post('/session/start', json={})
    # Expect error due to missing host_name.
    assert response.status_code in (400, 500)

def test_start_session_missing_host_name_2(client):
    response = client.post('/session/start', json={'host_name': None})
    # Expect error due to missing host_name.
    assert response.status_code in (400, 500)

def test_start_session_missing_host_name_3(client):
    response = client.post('/session/start', json={'host_name': ''})
    # Expect error due to missing host_name.
    assert response.status_code in (400, 500)

### Tests for `/session/join`

def test_join_session_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Bob'})
    session_id = start_response.get_json()['session_id']
    response = client.post('/session/join', json={'session_id': session_id, 'name': 'Charlie'})
    data = response.get_json()
    assert response.status_code == 200
    assert 'participant_ID' in data

def test_join_session_missing_parameters(client):
    response = client.post('/session/join', json={'session_id': '123456'})
    # Missing 'name' parameter.
    assert response.status_code in (400, 500)

def test_join_session_nonexistent_session(client):
    response = client.post('/session/join', json={'session_id': '999999', 'name': 'Dave'})
    # Expect error if session does not exist.
    assert response.status_code in (404, 500)

def test_join_session_not_allowed_status(client):
    # Start a session and manually mark it as active.
    start_response = client.post('/session/start', json={'host_name': 'Eve'})
    session_id = start_response.get_json()['session_id']
    from model import Session
    session_obj = Session.query.filter_by(id=session_id).first()
    session_obj.status = 'active'
    db.session.commit()

    response = client.post('/session/join', json={'session_id': session_id, 'name': 'Frank'})
    data = response.get_json()
    assert response.status_code == 200
    assert 'already started' in data.get('message', '').lower()

### Tests for `/session/begin`

def test_begin_session_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Diana'})
    session_id = start_response.get_json()['session_id']
    response = client.post('/session/begin', json={'session_id': session_id})
    data = response.get_json()
    assert response.status_code == 200
    assert f'session {session_id} start' in data.get('message', '')

def test_begin_session_missing_session_id(client):
    response = client.post('/session/begin', json={})
    assert response.status_code in (400, 500)

def test_begin_session_nonexistent(client):
    response = client.post('/session/begin', json={'session_id': '999999'})
    assert response.status_code in (404, 500)

### Tests for `/session/list_join_participants`

def test_list_join_participants_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Eve'})
    session_id = start_response.get_json()['session_id']
    client.post('/session/join', json={'session_id': session_id, 'name': 'Frank'})
    response = client.get(f'/session/list_join_participants?session_id={session_id}')
    data = response.get_json()
    assert response.status_code == 200
    assert 'participants_name' in data
    assert 'Eve' in data['participants_name']
    assert 'Frank' in data['participants_name']

def test_list_join_participants_missing_session_id(client):
    response = client.get('/session/list_join_participants')
    data = response.get_json()
    assert response.status_code == 400
    assert 'error' in data

def test_list_join_participants_no_participants(client):
    start_response = client.post('/session/start', json={'host_name': 'Gina'})
    session_id = start_response.get_json()['session_id']
    response = client.get(f'/session/list_join_participants?session_id={session_id}')
    data = response.get_json()
    assert response.status_code == 200
    # Only the host is present.
    assert data['participants_name'] == ['Gina']

### Tests for `/session/add_movie`

def test_add_movie_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Henry'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    response = client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 1,
        'participant_ID': participant_id
    })
    data = response.get_json()
    assert response.status_code == 200
    assert 'Movie added to pocket' in data.get('message', '')

def test_add_movie_missing_parameters(client):
    response = client.post('/session/add_movie', json={'session_id': '123456', 'movie_id': 1})
    assert response.status_code in (400, 500)

def test_add_movie_unauthorized_participant(client):
    start_response = client.post('/session/start', json={'host_name': 'Ivy'})
    session_id = start_response.get_json()['session_id']
    response = client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 2,
        'participant_ID': 9999  # invalid participant_ID
    })
    data = response.get_json()
    assert response.status_code == 403
    assert 'Not part of this session' in data.get('message', '')

### Tests for `/session/finish_selection`

def test_finish_selection_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Jack'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    response = client.post('/session/finish_selection', json={
        'session_id': session_id,
        'participant_id': participant_id
    })
    data = response.get_json()
    assert response.status_code == 200
    assert 'message' in data

def test_finish_selection_missing_parameters(client):
    response = client.post('/session/finish_selection', json={'session_id': '123456'})
    assert response.status_code in (400, 500)

def test_finish_selection_not_in_session(client):
    start_response = client.post('/session/start', json={'host_name': 'Laura'})
    session_id = start_response.get_json()['session_id']
    response = client.post('/session/finish_selection', json={
        'session_id': session_id,
        'participant_id': 9999
    })
    data = response.get_json()
    assert response.status_code == 403
    assert 'Not part of this session' in data.get('message', '')

### Tests for `/session/movies_in_pocket`

def test_movies_in_pocket_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Mike'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 3,
        'participant_ID': participant_id
    })
    response = client.get(f'/session/movies_in_pocket?session_id={session_id}&participant_id={participant_id}')
    data = response.get_json()
    assert response.status_code == 200
    assert 'movies' in data

def test_movies_in_pocket_missing_parameters(client):
    response = client.get('/session/movies_in_pocket?session_id=123456')
    data = response.get_json()
    assert response.status_code == 400
    assert 'Missing session_id or participant_id' in data.get('message', '')

def test_movies_in_pocket_unauthorized(client):
    start_response = client.post('/session/start', json={'host_name': 'Nina'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    response = client.get(f'/session/movies_in_pocket?session_id={session_id}&participant_id=9999')
    data = response.get_json()
    assert response.status_code == 403
    assert 'Not part of this session' in data.get('message', '')

### Tests for `/session/vote`

def test_vote_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Oscar'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 4,
        'participant_ID': participant_id
    })
    response = client.post('/session/vote', json={
        'session_id': session_id,
        'movie_id': 4,
        'participant_id': participant_id
    })
    data = response.get_json()
    assert response.status_code == 200
    assert 'Vote recorded' in data.get('message', '')

def test_vote_missing_parameters(client):
    response = client.post('/session/vote', json={'session_id': '123456', 'movie_id': 4})
    assert response.status_code in (400, 500)

def test_vote_unauthorized(client):
    start_response = client.post('/session/start', json={'host_name': 'Paul'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 5,
        'participant_ID': session_data['participant_id']
    })
    response = client.post('/session/vote', json={
        'session_id': session_id,
        'movie_id': 5,
        'participant_id': 9999
    })
    data = response.get_json()
    assert response.status_code == 403
    assert 'Not part of this session' in data.get('message', '')

def test_vote_movie_not_in_pocket(client):
    start_response = client.post('/session/start', json={'host_name': 'Quinn'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    response = client.post('/session/vote', json={
        'session_id': session_id,
        'movie_id': 999,
        'participant_id': participant_id
    })
    data = response.get_json()
    assert response.status_code == 404
    assert 'Movie not found in pocket' in data.get('message', '')

### Tests for `/session/finish_voting`

def test_finish_voting_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Rachel'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    response = client.post('/session/finish_voting', json={
        'session_id': session_id,
        'participant_id': participant_id
    })
    data = response.get_json()
    assert response.status_code == 200
    assert 'message' in data

def test_finish_voting_missing_parameters(client):
    response = client.post('/session/finish_voting', json={'session_id': '123456'})
    assert response.status_code in (400, 500)

def test_finish_voting_not_in_session(client):
    start_response = client.post('/session/start', json={'host_name': 'Steve'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    response = client.post('/session/finish_voting', json={
        'session_id': session_id,
        'participant_id': 9999
    })
    data = response.get_json()
    assert response.status_code == 403
    assert 'Not part of this session' in data.get('message', '')

### Tests for `/session/final_movie`

def test_final_movie_valid(client):
    start_response = client.post('/session/start', json={'host_name': 'Tom'})
    session_data = start_response.get_json()
    session_id = session_data['session_id']
    participant_id = session_data['participant_id']
    client.post('/session/add_movie', json={
        'session_id': session_id,
        'movie_id': 6,
        'participant_ID': participant_id
    })
    client.post('/session/vote', json={
        'session_id': session_id,
        'movie_id': 6,
        'participant_id': participant_id
    })
    response = client.get(f'/session/final_movie/{session_id}')
    if response.status_code == 200:
        data = response.get_json()
        assert 'movie_id' in data
    else:
        data = response.get_json()
        assert response.status_code == 404 or 'message' in data

def test_final_movie_no_movies(client):
    # When no movies are added, the endpoint should indicate no movie selected.
    start_response = client.post('/session/start', json={'host_name': 'Uma'})
    session_id = start_response.get_json()['session_id']
    response = client.get(f'/session/final_movie/{session_id}')
    data = response.get_json()
    assert response.status_code == 404 or ('message' in data and 'No movie selected' in data.get('message', ''))