import pytest
from datetime import datetime
from extentions import db
from model import Movie

def create_movie(db, title="Test Movie", genres="Drama", original_language="en",
                 overview="A test movie", popularity=7.5,
                 release_date=datetime(2021, 1, 1), poster_path="test.jpg"):
    movie = Movie(title=title, genres=genres, original_language=original_language,
                  overview=overview, popularity=popularity,
                  release_date=release_date, poster_path=poster_path)
    db.session.add(movie)
    db.session.commit()
    return movie

### Tests for the `/movies/search` endpoint

def test_search_movies_valid_query(client):
    # Create a movie that matches the search query.
    create_movie(db, title="Searchable Movie")
    response = client.get('/movies/search?query=Searchable')
    data = response.get_json()
    assert response.status_code == 200
    assert any("Searchable Movie" in movie['title'] for movie in data)

def test_search_movies_empty_query(client):
    # Empty query should return an empty list.
    response = client.get('/movies/search?query=')
    data = response.get_json()
    assert response.status_code == 200
    assert data == []

def test_search_movies_no_match(client):
    # Query that does not match any movie should return an empty list.
    response = client.get('/movies/search?query=Nonexistent')
    data = response.get_json()
    assert response.status_code == 200
    assert data == []

### Tests for `/movies/get_all_movies`

def test_get_all_movies_empty_db(client):
    # When there are no movies, an empty list should be returned.
    response = client.get('/movies/get_all_movies')
    data = response.get_json()
    assert response.status_code == 200
    assert isinstance(data, list)

def test_get_all_movies_limit(client):
    # Insert more than 10 movies to test the limit constraint.
    for i in range(10, 22):
        create_movie(db, title=f"Movie {i}")
    response = client.get('/movies/get_all_movies')
    data = response.get_json()
    assert response.status_code == 200
    # Endpoint uses limit(10), so length should be at most 10.
    assert len(data) <= 10

### Tests for `/movies/sort_movies`

def test_sort_movies_valid(client):
    create_movie(db, title="Low Popularity", popularity=3)
    create_movie(db, title="High Popularity", popularity=9999.0)
    response = client.get('/movies/sort_movies?sort_by=popularity&order=desc')
    data = response.get_json()
    assert response.status_code == 200
    # The first movie should have the higher popularity.
    assert data[0]['title'] == "High Popularity"

def test_sort_movies_invalid_sort_field(client):
    response = client.get('/movies/sort_movies?sort_by=invalid_field')
    data = response.get_json()
    assert response.status_code == 400
    assert 'error' in data

def test_sort_movies_invalid_order(client):
    # If order parameter is invalid, endpoint may default to ascending.
    response = client.get('/movies/sort_movies?sort_by=title&order=invalid')
    data = response.get_json()
    assert response.status_code == 200
    assert isinstance(data, list)

### Tests for `/movies/filter_movies`

def test_filter_movies_valid(client):
    create_movie(db, title="Filtered Movie", genres="Action", original_language="fr",
                 release_date=datetime(2021, 5, 20))
    response = client.get('/movies/filter_movies?language=fr&release_year=2021&genres=Action')
    data = response.get_json()
    assert response.status_code == 200
    for movie in data:
        assert movie['original_language'] == "fr"
        assert "2021" in movie['release_date']

def test_filter_movies_no_match(client):
    response = client.get('/movies/filter_movies?language=xx&release_year=1900&genres=Unknown')
    data = response.get_json()
    assert response.status_code == 200
    assert data == []

def test_filter_movies_invalid_release_year(client):
    # Passing a non-integer for release_year might cause an error or return an empty list.
    response = client.get('/movies/filter_movies?release_year=not_a_number')
    data = response.get_json()
    assert response.status_code in (200, 400)

### Tests for `/movies/get_movie_info_by_ids`

def test_get_movie_info_by_ids_valid(client):
    movie_1 = create_movie(db, title="Movie 300")
    movie_2 = create_movie(db, title="Movie 301")
    payload = {"ids": [movie_1.id, movie_2.id]}
    response = client.post('/movies/get_movie_info_by_ids', json=payload)
    data = response.get_json()
    assert response.status_code == 200
    assert len(data) == 2

def test_get_movie_info_by_ids_empty_ids(client):
    payload = {"ids": []}
    response = client.post('/movies/get_movie_info_by_ids', json=payload)
    data = response.get_json()
    assert response.status_code == 200
    assert data == []

def test_get_movie_info_by_ids_missing_json(client):
    response = client.post('/movies/get_movie_info_by_ids')
    # Expect an error due to missing JSON body.
    assert response.status_code in (400, 500)

def test_get_movie_info_by_ids_some_not_found(client):
    movie = create_movie(db, title="Movie 400")
    payload = {"ids": [movie.id, 99999999]}
    test_id = movie.id
    response = client.post('/movies/get_movie_info_by_ids', json=payload)
    data = response.get_json()
    assert response.status_code == 200
    # Assuming the endpoint returns available records.
    assert any(movie['id'] == test_id for movie in data)