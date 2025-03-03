from flask import Blueprint, request, jsonify
from model import Movie
from extentions import db
movie_bp = Blueprint('movies', __name__)


@movie_bp.route('/search', methods=['GET'])
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


@movie_bp.route('/get_movie_info_by_id', methods=['GET'])
def Get_info_id():
    movie_id = request.args.get('id')

    movie = Movie.query.filter_by(id=movie_id).first()

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

@movie_bp.route('/get_movie_info_by_ids', methods=['GET'])
def Get_info_ids():
    data = request.json
    movie_ids = data.get('ids')
    results = []
    for movie_id in movie_ids:
        movie = Movie.query.filter_by(id=movie_id).first()

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
        results.append(result)

    return jsonify(results)


