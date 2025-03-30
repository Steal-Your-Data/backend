from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

from model import Movie
from extentions import db
from sqlalchemy import extract
movie_bp = Blueprint('movies', __name__)


@movie_bp.route('/search', methods=['GET'])
@cross_origin()
def search_movies():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    movies = Movie.query.filter(Movie.title.ilike(f'%{query}%')).limit(10).all()
    result = []
    for movie in movies:
        result.append({
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        })
    return jsonify(result)


@movie_bp.route('/get_movie_info_by_id', methods=['POST'])
@cross_origin()
def Get_info_id():
    movie_id = request.args.get('id')
    if not movie_id:
        return jsonify({'error': 'Missing movie id parameter'}), 400

    data = request.json
    movie_id = data.get('id')

    movie = Movie.query.filter_by(id=movie_id).first()
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    result = {
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        }

    return jsonify(result)

@movie_bp.route('/get_all_movies', methods=['GET'])
@cross_origin()
def get_all_movies():
    movies = Movie.query.limit(10).all()  # REMOVE limit(10) to get all movies
    result = []

    for movie in movies:
        result.append({
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        })

    return jsonify(result)

@movie_bp.route('/sort_movies', methods=['GET'])
@cross_origin()
def sort_movies():
    sort_by = request.args.get('sort_by', 'title')  # Default to sorting by title
    order = request.args.get('order', 'asc').lower()  # Default to ascending order

    valid_sort_columns = {
        'popularity': Movie.popularity,
        'release_date': Movie.release_date,
        'title': Movie.title
    }

    if sort_by not in valid_sort_columns:
        return jsonify({'error': 'Invalid sort field'}), 400

    # Sort movies based on user request
    query = Movie.query.order_by(
        valid_sort_columns[sort_by].desc() if order == 'desc' else valid_sort_columns[sort_by].asc()
    )

    movies = query.all()
    
    result = [
        {
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        }
        for movie in movies
    ]
    
    return jsonify(result)


@movie_bp.route('/filter_movies', methods=['GET'])
@cross_origin()
def filter_movies():
    genres = request.args.getlist('genres')  # Expect a list of genres
    language = request.args.get('language')
    release_year = request.args.get('release_year', type=int)

    query = Movie.query

    # Filter by genres (matches at least one selected genre)
    if genres:
        genre_filters = [Movie.genres.ilike(f"%{genre}%") for genre in genres]
        query = query.filter(db.or_(*genre_filters))

    # Filter by language
    if language:
        query = query.filter(Movie.original_language == language)

    # Filter by release year
    if release_year:
        query = query.filter(extract('year', Movie.release_date) == release_year)

    movies = query.all()

    result = [
        {
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        }
        for movie in movies
    ]

    return jsonify(result)


@movie_bp.route('/get_movie_info_by_ids', methods=['POST'])
@cross_origin()
def Get_info_ids():
    data = request.json
    movie_ids = data.get('ids')
    if not movie_ids:
        return jsonify([]), 200

    results = []
    for movie_id in movie_ids:
        movie = Movie.query.filter_by(id=movie_id).first()
        if movie is None:
            continue  # Skip IDs that don't match any movie.
        results.append({
            'id': movie.id,
            'title': movie.title,
            'genres': movie.genres,
            'original_language': movie.original_language,
            'overview': movie.overview,
            'popularity': movie.popularity,
            'release_date': movie.release_date.isoformat() if movie.release_date else None,
            'poster_path': movie.poster_path
        })

    return jsonify(results)