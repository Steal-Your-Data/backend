from routes.Config import TMDB_api, genre_dict, genre_dict_rev
import requests

def get_filtered_now_playing(page, genres, language, release_year, per_page=12):
    """
    Fetch now-playing movies from TMDb, apply additional filters (genres, language, release_year),
    and return a paginated list (per_page movies per page) of filtered movies.
    """
    filtered_results = []
    tmdb_now_playing_url = "https://api.themoviedb.org/3/movie/now_playing"
    current_page = 1
    total_pages = None

    while True:
        params = {
            'api_key': TMDB_api,
            'language': 'en-US',
            'page': current_page,
            'region': 'US'
        }
        response = requests.get(tmdb_now_playing_url, params=params)
        response.raise_for_status()
        data = response.json()
        if total_pages is None:
            total_pages = data.get('total_pages', 1)
        now_playing_movies = data.get('results', [])
        for movie in now_playing_movies:
            # Map genre_ids to genre names for filtering
            movie_genre_names = [genre_dict.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
            # Filter by genres: check if any filter genre appears in any movie genre name
            if genres:
                if not any(filter_genre.lower() in mg.lower() for filter_genre in genres for mg in movie_genre_names):
                    continue
            # Filter by language
            if language and movie.get('original_language') != language:
                continue
            # Filter by release year
            if release_year:
                movie_release_date = movie.get('release_date')
                if movie_release_date:
                    try:
                        movie_year = int(movie_release_date.split('-')[0])
                    except Exception:
                        movie_year = None
                    if movie_year != release_year:
                        continue
                else:
                    continue
            filtered_results.append(movie)
        # If we've accumulated enough filtered movies for the requested page, break out
        if len(filtered_results) >= page * per_page:
            break
        current_page += 1
        if current_page > total_pages:
            break

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    return filtered_results[start_index:end_index]


def get_filtered(page, genres, language, release_year, sort_by='popularity', order='desc', per_page=12):
    """
    Fetch movies from TMDb Discover API and map genres back to names.
    """
    # Map genre names to IDs
    genre_ids = [str(genre_dict_rev[g.strip()]) for g in genres if g.strip() in genre_dict_rev]
    # Build request parameters
    params = {
        'api_key': TMDB_api,
        'with_genres': ','.join(genre_ids),
        'with_genres_operator': 'or',
        'sort_by': f"{sort_by}.{order}",
        'page': page
    }
    if release_year:
        params['primary_release_year'] = release_year
    if language:
        params['with_original_language'] = language

    response = requests.get("https://api.themoviedb.org/3/discover/movie", params=params)
    response.raise_for_status()
    data = response.json()

    formatted_results = []
    for movie in data.get('results', [])[:per_page]:
        movie_genre_names = [genre_dict.get(gid, 'Unknown') for gid in movie.get('genre_ids', [])]
        genres_str = '-'.join(movie_genre_names) if movie_genre_names else 'Unknown'
        formatted_results.append({
            'id': movie.get('id'),
            'title': movie.get('title'),
            'genres': genres_str,
            'original_language': movie.get('original_language'),
            'overview': movie.get('overview'),
            'popularity': movie.get('popularity'),
            'release_date': movie.get('release_date'),
            'poster_path': movie.get('poster_path')
        })
    return formatted_results