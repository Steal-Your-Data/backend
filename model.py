from extentions import db
from flask_login import UserMixin



'''
---------------------------------------------------------------------------
If V2, This is useless
'''
# User Model
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Friendship Model for Friend Requests
class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted

'''
----------------------------------------------------------------------------
If V2, This is useless
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
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who started the session
    status = db.Column(db.String(20), default='pending')  # pending, active, completed


'''
------------------------------------------------------------------------------------
If V2, modify session_participant, since we do not have 
user_id, we probably just use name for user_id part
'''

# Participants in a Session
class SessionParticipant(db.Model):
    __tablename__ = 'session_participant'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)  # NEW COLUMN for session confirmation
    done_selecting = db.Column(db.Boolean, default=False)  # For movie selection phase
    done_voting = db.Column(db.Boolean, default=False)  # For voting phase


'''
------------------------------------------------------------------------------------
If V2, modify session_participant, since we do not have 
user_id, we probably just use name for user_id part
'''



# Temporary Pocket for Movie Voting
class MoviePocket(db.Model):
    __tablename__ = 'movie_pocket'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'))
    votes = db.Column(db.Integer, default=0)


'''
---------------------------------------------------------------------------
If V2, This is useless
'''
class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'  # Define table name
    id = db.Column(db.Integer, primary_key=True)  # Auto-increment ID
    jti = db.Column(db.String(36), unique=True, nullable=False)  # Store JWT ID

    def __init__(self, jti):
        self.jti = jti

    def save_to_db(self):
        """ Save revoked token to the database """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def is_token_blacklisted(cls, jti):
        """ Check if a token is in the blacklist """
        return db.session.query(cls).filter_by(jti=jti).first() is not None

'''
----------------------------------------------------------------------------
If V2, This is useless
'''