import os
'''
     Config.py
     This file contains configuration settings and mappings for the movie app, including:
     - TMDB API key retrieval
     - Genre ID to name mappings (genre_dict)
     - Genre name to ID mappings (genre_dict_rev)
'''
# Retrieve TMDB API key from environment variable, with a default fallback key
TMDB_api = os.environ.get('TMDB_KEY', '454688fc07a43e24f8dd4952f05c413f')

# Mapping from TMDB genre IDs to genre names
genre_dict = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western"
}
# Reverse mapping from genre names back to TMDB genre IDs
genre_dict_rev = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "TV Movie": 10770,
    "Thriller": 53,
    "War": 10752,
    "Western": 37
}