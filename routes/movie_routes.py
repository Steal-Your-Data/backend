from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from model import Movie
from extentions import db
from sqlalchemy import extract
from routes.Config import TMDB_api,genre_dict
import requests
from routes.Utils import get_filtered_now_playing, get_filtered, discover_movies
from datetime import date
movie_bp = Blueprint('movies', __name__)

'''
    movie_routes.py
    
    This file defines the Flask Blueprint routes for managing movie-related operations.
    It handles:
    - Searching for movies in the local database and via TMDb API
    - Retrieving detailed movie information by ID
    - Listing movies with pagination support
    - Sorting and filtering movies based on various attributes
    - Combining filtering and sorting operations
    Utility functions and external TMDb API are used to enrich movie data retrieval.
'''

#
# ------------------------------- Movie Search Routes --------------------------------
# Provides endpoints for searching movies either from the local database or TMDb API.
#
'''--------------------------------------Movie Search-----------------------------------------------------'''
#
# Search movies in the local database (up to 10 matches)
#
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

#
# Search movies using TMDb external API (supports pagination)
#
@movie_bp.route('/search_API', methods=['GET'])
def search_movies_API():
    query = request.args.get('query', '').strip()
    page  = request.args.get('page', 1, type=int)  # ← new: page number (defaults to 1)

    if not query:
        return jsonify([])

    tmdb_search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': TMDB_api,
        'query': query,
        'language': 'en-US',
        'page': page,           # ← new: pass the page through
        'include_adult': False
    }

    try:
        response = requests.get(tmdb_search_url, params=params)
        response.raise_for_status()
        data    = response.json()
        movies  = data.get('results', [])

        today = date.today()

        result = []
        for movie in movies:    # ← no artificial 10‑item cap
            release_date_str = movie.get('release_date')
            if not release_date_str:
                continue  # Skip movies without a release date
            try:
                release_date = date.fromisoformat(release_date_str)
                if release_date > today:
                    continue  # Skip future release movies
            except ValueError:
                continue  # Skip movies with malformed release date
            genre_names = [
                genre_dict.get(gid, "Unknown")
                for gid in movie.get('genre_ids', [])
            ]
            result.append({
                'id'               : movie.get('id'),
                'title'            : movie.get('title'),
                'genres'           : '-'.join(genre_names) or "Unknown",
                'original_language': movie.get('original_language'),
                'overview'         : movie.get('overview'),
                'popularity'       : movie.get('popularity'),
                'release_date'     : movie.get('release_date'),
                'poster_path'      : movie.get('poster_path')
            })

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500




'''-------------------------------------------------------------Get_info_id-------------------------------------------'''


#
# Get detailed movie information by movie ID from TMDb API
#
@movie_bp.route('/get_movie_info_by_id_API', methods=['GET'])
def get_info_by_id_API():
    movie_id = request.args.get('id')
    if not movie_id:
        return jsonify({'error': 'Missing movie id parameter'}), 400

    tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        'api_key': TMDB_api,
        'language': 'en-US'
    }

    try:
        response = requests.get(tmdb_url, params=params)
        response.raise_for_status()
        movie = response.json()

        # Extract genre names and join them with a dash
        genre_names = [genre['name'] for genre in movie.get('genres', [])]
        genres_str = '-'.join(genre_names) if genre_names else "Unknown"

        result = {
            'id': movie.get('id'),
            'title': movie.get('title'),
            'genres': genres_str,
            'original_language': movie.get('original_language'),
            'overview': movie.get('overview'),
            'popularity': movie.get('popularity'),
            'release_date': movie.get('release_date'),
            'poster_path': movie.get('poster_path')
        }

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

#
# Get a limited set of movies (15) from the local database
#
@movie_bp.route('/get_all_movies', methods=['GET'])
@cross_origin()
def get_all_movies():
    movies = Movie.query.limit(15).all()  # REMOVE limit(10) to get all movies
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

#
# Get movies from the local database with pagination (12 per page)
#
@movie_bp.route('/get_all_movies_V2', methods=['GET'])
def get_all_movies_V2():
    try:
        # Get the page number from query parameters, default to 1 if not provided
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError("Page must be a positive integer.")
    except ValueError:
        return jsonify({'error': 'Invalid page number. Page must be a positive integer.'}), 400

    per_page = 12
    offset = (page - 1) * per_page

    # Fetch the appropriate page of movies
    movies = Movie.query.offset(offset).limit(per_page).all()
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

#
# Get popular movies from TMDb API with pagination (up to 12 results)
#
@movie_bp.route('/get_all_movies_API', methods=['GET'])
def get_all_movies_API():
    page = request.args.get('page', 1, type=int)
    tmdb_url = "https://api.themoviedb.org/3/movie/popular"
    params = {
        'api_key': TMDB_api,
        'language': 'en-US',
        'page': page
    }

    try:
        response = requests.get(tmdb_url, params=params)
        response.raise_for_status()
        data = response.json()
        movies = data.get('results', [])

        result = []
        for movie in movies:
            genre_names = [genre_dict.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
            genres_str = '-'.join(genre_names) if genre_names else "Unknown"
            result.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'genres': genres_str,
                'original_language': movie.get('original_language'),
                'overview': movie.get('overview'),
                'popularity': movie.get('popularity'),
                'release_date': movie.get('release_date'),
                'poster_path': movie.get('poster_path')
            })
            if len(result) == 12:
                break

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500




'''--------------------------------------------sort movies------------------------------------'''
#
# Sort all local movies by a specified field (popularity, release date, or title)
#
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

#
# Sort local movies with pagination (12 movies per page)
#
@movie_bp.route('/sort_movies_V2', methods=['GET'])
def sort_movies_V2():
    sort_by = request.args.get('sort_by', 'title')  # Default to sorting by title
    order = request.args.get('order', 'asc').lower()  # Default to ascending order

    valid_sort_columns = {
        'popularity': Movie.popularity,
        'release_date': Movie.release_date,
        'title': Movie.title
    }

    if sort_by not in valid_sort_columns:
        return jsonify({'error': 'Invalid sort field'}), 400

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Invalid page number. Must be a positive integer.'}), 400

    per_page = 12
    offset = (page - 1) * per_page

    query = Movie.query.order_by(
        valid_sort_columns[sort_by].desc() if order == 'desc' else valid_sort_columns[sort_by].asc()
    )

    movies = query.offset(offset).limit(per_page).all()

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


'''-----------------------------------------------filter_movies----------------------------------------'''
#
# Filter local movies by genres, language, and release year
#
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


#
# Get multiple movie details from the local database by their IDs (POST request)
#
@movie_bp.route('/get_movie_info_by_ids', methods=['POST'])
@cross_origin()
def get_info_ids():
    # Force JSON parsing for GET (even if no Content-Type is provided)
    data = request.get_json(silent=True, force=True)
    if not data:
        return jsonify({'error': 'Missing movie id json'}), 400

    if 'ids' not in data:
        return jsonify({'error': 'Missing "ids" key in JSON'}), 400

    movie_ids = data.get('ids')
    if movie_ids == []:
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

#
# Get multiple movie details from TMDb API by their IDs (POST request)
#
@movie_bp.route('/get_movie_info_by_ids_API', methods=['POST'])
def get_info_ids_API():

    data = request.get_json(silent=True, force=True)
    if not data:
        return jsonify({'error': 'Missing movie id json'}), 400

    if 'ids' not in data:
        return jsonify({'error': 'Missing "ids" key in JSON'}), 400

    ids = data.get('ids')
    if ids == []:
        return jsonify([]), 200
    
    results = []
    for movie_id in ids:
        tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            'api_key': TMDB_api,
            'language': 'en-US'
        }

        try:
            response = requests.get(tmdb_url, params=params)
            response.raise_for_status()
            movie = response.json()

            # Extract genre names and join them with a dash
            genre_names = [genre['name'] for genre in movie.get('genres', [])]
            genres_str = '-'.join(genre_names) if genre_names else "Unknown"

            result = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'genres': genres_str,
                'original_language': movie.get('original_language'),
                'overview': movie.get('overview'),
                'popularity': movie.get('popularity'),
                'release_date': movie.get('release_date'),
                'poster_path': movie.get('poster_path')
            }
            results.append(result)

        except requests.RequestException as e:
            return jsonify({'error': str(e)}), 500

    return jsonify(results)

#
# Filter local or now-playing movies with pagination and genre/language/year filters
#
@movie_bp.route('/filter_movies_V2', methods=['GET'])
def filter_movies_V2():
    genres = request.args.getlist('genres')  # Expect a list of genres
    language = request.args.get('language')
    release_year = request.args.get('release_year', type=int)
    only_in_theater = True if request.args.get('only_in_theater') == 'yes' else False

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Invalid page number. Must be a positive integer.'}), 400

    per_page = 12
    offset = (page - 1) * per_page

    # If only_in_theater is True, fetch now-playing movies from TMDb via the helper function
    if only_in_theater:
        # from Utils import get_filtered_now_playing  # Import the helper function from Utils.py
        now_playing_movies = get_filtered_now_playing(page, genres, language, release_year, per_page=12)
        results = []
        for movie in now_playing_movies:
            movie_genre_names = [genre_dict.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
            genres_str = '-'.join(movie_genre_names) if movie_genre_names else "Unknown"
            results.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'genres': genres_str,
                'original_language': movie.get('original_language'),
                'overview': movie.get('overview'),
                'popularity': movie.get('popularity'),
                'release_date': movie.get('release_date'),
                'poster_path': movie.get('poster_path')
            })
        return jsonify(results)

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

    movies = query.offset(offset).limit(per_page).all()

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

#
# Filter and sort movies, either from the https://api.themoviedb.org/3/discover/movie or https://api.themoviedb.org/3/movie/now_playing from TMDb
#
@movie_bp.route('/filter_and_sort', methods=['GET'])
def filter_and_sort():
    genres = request.args.getlist('genres')  # Expect a list of genres
    language = request.args.get('language')
    release_year = request.args.get('release_year', type=int)
    only_in_theater = True if request.args.get('only_in_theater') == 'yes' else False

    sort_by = request.args.get('sort_by')
    order = request.args.get('order')

    if not sort_by:
        sort_by = 'release_date'

    if not order:
        order = 'desc'  # Default to ascending order if not specified
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Invalid page number. Must be a positive integer.'}), 400

    per_page = 12
    # offset = (page - 1) * per_page

    # If only_in_theater is True, fetch now-playing movies from TMDb via the helper function
    if only_in_theater:
        # from Utils import get_filtered_now_playing  # Import the helper function from Utils.py
        now_playing_movies = get_filtered_now_playing(page, genres, language, release_year, per_page=12)
        results = []
        for movie in now_playing_movies:
            movie_genre_names = [genre_dict.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
            genres_str = '-'.join(movie_genre_names) if movie_genre_names else "Unknown"
            results.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'genres': genres_str,
                'original_language': movie.get('original_language'),
                'overview': movie.get('overview'),
                'popularity': movie.get('popularity'),
                'release_date': movie.get('release_date'),
                'poster_path': movie.get('poster_path')
            })
        return jsonify(results)

    # Otherwise use TMDb Discover API for filtering, sorting, and formatting
    filtered_movies = get_filtered(page, genres, language, release_year, sort_by, order, per_page=12)
    return jsonify(filtered_movies)

#
# Advanced filter and sort from TMDb API with support for release year range
#
@movie_bp.route("/filter_and_sort_V2", methods=["GET"])
def filter_and_sort_V2():
    # ------------------------------------------------------------------ query params
    genres = request.args.get("genres")
    language = request.args.get("language")
    only_in_theater = request.args.get("only_in_theater") == "yes"

    sort_by = request.args.get("sort_by", "release_date")
    order = request.args.get("order", "desc")

    # year‑range
    release_year_min = request.args.get("release_year_min", type=int)
    release_year_max = request.args.get("release_year_max", type=int)

    # validate / normalise year‑range ------------------------------------------
    year_range = None
    if release_year_min is not None or release_year_max is not None:
        # if one bound missing, assume a single‑year range
        if release_year_min is None:
            release_year_min = release_year_max
        if release_year_max is None:
            release_year_max = release_year_min

        if release_year_min > release_year_max:
            return jsonify({
                "error": "`release_year_min` cannot be greater than `release_year_max`."
            }), 400

        year_range = (release_year_min, release_year_max)

    # page ---------------------------------------------------------------------
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid page number. Must be a positive integer."}), 400

    # ------------------------------------------------------------------ TMDb call
    try:
        payload = discover_movies(
            page=page,
            genres=genres.split("|") if genres else None,
            language=language,
            year_range=year_range,
            sort_by=sort_by,
            order=order,
            now_playing=only_in_theater
        )
    except requests.HTTPError as exc:
        return jsonify({"error": "TMDb request failed", "detail": str(exc)}), 502

    return jsonify(payload["results"])