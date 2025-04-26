from extentions import db
from sqlalchemy.dialects.sqlite import TEXT
import uuid
import random

'''
    model.py
    
    This file defines the SQLAlchemy models for the application database, including:
    - Movie: Stores information about individual movies
    - Session: Represents a movie selection session with a host and status
    - SessionParticipant: Tracks participants in a session and their progress
    - MoviePocket: Temporary storage for selected movies and their votes during a session
'''


class Movie(db.Model):
    __tablename__ = 'movies'  # Ensure the table name matches your CSV import
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genres = db.Column(db.String(100))
    original_language = db.Column(db.String(10))
    overview = db.Column(db.Text)
    popularity = db.Column(db.Float)
    release_date = db.Column(db.Date)
    poster_path = db.Column(db.String(200))


# Session Model for movie sessions
class Session(db.Model):
    __tablename__ = 'session'
    id = db.Column(TEXT, primary_key=True, default = str(random.randint(100000, 999999)))  # Unique random ID
    host_name = db.Column(db.String(255), nullable=False)  # Regular string for host name
    status = db.Column(db.String(20), default='pending')  # pending, active, completed

# Participants in a Session
class SessionParticipant(db.Model):
    __tablename__ = 'session_participant'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text, db.ForeignKey('session.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # Name column
    done_selecting = db.Column(db.Boolean, default=False)  # For movie selection phase
    done_voting = db.Column(db.Boolean, default=False)  # For voting phase



# Temporary Pocket for Movie Voting
class MoviePocket(db.Model):
    __tablename__ = 'movie_pocket'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text, db.ForeignKey('session.id'),nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'))
    votes = db.Column(db.Integer, default=0)
