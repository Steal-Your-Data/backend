from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

from model import Movie
from extentions import db
from sqlalchemy import extract
from routes.Config import TMDB_api,genre_dict
import requests
from routes.Utils import get_filtered_now_playing
movie_bp = Blueprint('movies', __name__)

'''--------------------------------------Movie Search-----------------------------------------------------'''
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

'''Not search the local database now, but just do search from the API'''
@movie_bp.route('/search_API', methods=['GET'])
def search_movies_API():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    tmdb_search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': TMDB_api,
        'query': query,
        'language': 'en-US',
        'page': 1,
        'include_adult': False
    }

    try:
        response = requests.get(tmdb_search_url, params=params)
        response.raise_for_status()
        data = response.json()
        movies = data.get('results', [])

        result = []
        for movie in movies[:10]:  # Limit to 10 results
            genre_names = [genre_dict.get(genre_id, "Unknown") for genre_id in movie.get('genre_ids', [])]
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

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500




'''-------------------------------------------------------------Get_info_id-------------------------------------------'''


'''Now not get the movie information from local database but from the OPEN API'''
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

'''------------------------------------------------------Get ALL MOVIES----------------------------------'''


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

'''Get_all_movies by only loading 10 movies each time not a whole'''
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




'''--------------------------------------------sort movies------------------------------------'''
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

'''Same as befoe each time only return specific 10 movies in this page'''
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


# @movie_bp.route('/get_movie_info_by_ids', methods=['GET'])
# def get_info_ids():
#     data = request.json
#     if data is None:
#         return jsonify({'error': 'Missing movie id JSON'}), 400
#
#     if 'ids' not in data:
#         return jsonify({'error': 'Missing "ids" key in JSON'}), 400
#
#
#     movie_ids = data.get('ids')
#
#     if not movie_ids:
#         return jsonify({'error': 'No movie ids provided'}), 400
#     if len(movie_ids) == 0:
#         return jsonify({'error': 'The movie ids list is empty'}), 200
#
#     results = []
#     for movie_id in movie_ids:
#         movie = Movie.query.filter_by(id=movie_id).first()
#         if movie:
#             result = {
#                 'id': movie.id,
#                 'title': movie.title,
#                 'genres': movie.genres,
#                 'original_language': movie.original_language,
#                 'overview': movie.overview,
#                 'popularity': movie.popularity,
#                 'release_date': movie.release_date.isoformat() if movie.release_date else None,
#                 'poster_path': movie.poster_path
#             }
#             results.append(result)
#     if not results:
#         # Option 1: return an empty list (status 200)
#         # return jsonify([]), 200
#
#         # Option 2: return an error if none were found
#         return jsonify({'error': 'No movies found for provided ids'}), 404
#
#     return jsonify(results)
# @movie_bp.route('/get_movie_info_by_ids', methods=['GET'])
# def get_info_ids():
#     data = request.json(silent=True,force=True)
#     if data is None:
#         return jsonify({'error': 'Missing movie id json'}), 400
#
#     if 'ids' not in data:
#         return jsonify({'error': 'Missing "ids" key in JSON'}), 400
#
#     movie_ids = data.get('ids')
#     # If the list is empty, return an empty list with status 200
#     if movie_ids == []:
#         return jsonify([]), 200
#
#     results = []
#     for movie_id in movie_ids:
#         movie = Movie.query.filter_by(id=movie_id).first()
#         # Only add movie info if the movie exists.
#         if movie is not None:
#             result = {
#                 'id': movie.id,
#                 'title': movie.title,
#                 'genres': movie.genres,
#                 'original_language': movie.original_language,
#                 'overview': movie.overview,
#                 'popularity': movie.popularity,
#                 'release_date': movie.release_date.isoformat() if movie.release_date else None,
#                 'poster_path': movie.poster_path
#             }
#             results.append(result)
#     return jsonify(results)


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

'''get movie informations from API instead of local database'''
@movie_bp.route('/get_movie_info_by_ids_API', methods=['GET'])
def get_info_ids_API():
    ids = request.args.getlist('ids')
    if not ids:
        return jsonify({'error': 'Missing movie id parameter'}), 400
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

    # Sorting logic
    if sort_by:
        if sort_by == "popularity":
            sort_column = Movie.popularity
        elif sort_by == "title":
            sort_column = Movie.title
        elif sort_by == "release_date":
            sort_column = Movie.release_date
        else:
            return jsonify(
                {'error': 'Invalid sort_by parameter. Must be one of: popularity, title, release_date.'}), 400

        if order == "asc":
            query = query.order_by(sort_column.asc())
        elif order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            return jsonify({'error': 'Invalid order parameter. Must be one of: asc, desc.'}), 400
    else:
        # If no sort_by is provided, you can return an error or default to a field like title.
        query = query.order_by(Movie.title.asc())

    # Paginate the results
    movies = query.offset(offset).limit(per_page).all()

    # Prepare the results to be returned
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
