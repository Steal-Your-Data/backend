from flask import Blueprint, request, jsonify
from extentions import db,login_manager

from model import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_login import login_user, logout_user
from model import RevokedToken  # Import the model
from flask_jwt_extended import get_jwt


auth_bp = Blueprint('auth', __name__)

# invalidated_tokens = set()

'''if V2, no need for this'''


# Register New User
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')  # Remember: hash the password in production!

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400

    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201


# User Login: returns JWT access token
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or user.password != password:
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=str(user.id))
    login_user(user)
    return jsonify({'access_token': access_token, 'user_id': user.id, 'username': user.username,'expires_in': 60 * 60 * 24})



@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = get_jwt_identity()  # Get user ID from JWT
    jti = get_jwt()["jti"]  # Get JWT unique identifier

    # Store the token in the database
    revoked_token = RevokedToken(jti=jti)
    revoked_token.save_to_db()

    logout_user()  # Logout from Flask-Login session

    return jsonify({'message': f'User {user_id} logged out successfully'}), 200

# Get User Profile
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({'user_id': user.id, 'username': user.username, 'email': user.email})
