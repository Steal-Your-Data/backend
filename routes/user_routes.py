from flask import Blueprint, request, jsonify
from extentions import db, socketio
from model import User, Friendship
from flask_jwt_extended import jwt_required, get_jwt_identity

user_bp = Blueprint('user', __name__)


# Send a Friend Request
@user_bp.route('/send_friend_request', methods=['POST'])
@jwt_required()
def send_friend_request():
    user_id = get_jwt_identity()
    data = request.json
    friend_email = data.get('email')

    friend = User.query.filter_by(email=friend_email).first()
    if not friend:
        return jsonify({'message': 'User not found'}), 404

    existing_request = Friendship.query.filter_by(user_id=user_id, friend_id=friend.id).first()
    if existing_request:
        return jsonify({'message': 'Friend request already sent'}), 400

    new_request = Friendship(user_id=user_id, friend_id=friend.id, status='pending')
    db.session.add(new_request)
    db.session.commit()

    sender = User.query.get(user_id)
    socketio.emit('friend_request',
                  {
                   'request_id': new_request.id, # Unique transaction ID
                   'from_user_id': user_id,
                   'from_username': sender.username
                  },
                  room=f'notif_{friend.id}')
    return jsonify({'message': 'Friend request sent'})


# Accept or Reject Friend Request
@user_bp.route('/respond_friend_request', methods=['POST'])
@jwt_required()
def respond_friend_request():
    user_id = get_jwt_identity()
    data = request.json
    request_id = data.get('request_id')
    action = data.get('action')  # "accept" or "reject"

    friend_request = Friendship.query.get(request_id)
    if not friend_request or friend_request.friend_id != int(user_id):
        return jsonify({'message': 'Friend request not found'}), 404

    if action == "accept":
        friend_request.status = "accepted"
        db.session.commit()
        responder = User.query.get(user_id)
        # Fixed missing quote in room specification:
        socketio.emit('friend_request_accepted',
                      {'from_user_id': user_id, 'from_username': responder.username},
                      room=f'notif_{friend_request.user_id}')
        return jsonify({'message': 'Friend request accepted'})
    elif action == "reject":
        db.session.delete(friend_request)
        db.session.commit()
        return jsonify({'message': 'Friend request rejected'})
    else:
        return jsonify({'message': 'Invalid action'}), 400


# Get Friend List
@user_bp.route('/friend_list', methods=['GET'])
@jwt_required()
def friend_list():
    user_id = get_jwt_identity()
    friendships = Friendship.query.filter(
        ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)) &
        (Friendship.status == 'accepted')
    ).all()

    friends = []
    for f in friendships:
        friend_id = f.friend_id if f.user_id == int(user_id) else int(f.user_id)
        friend = User.query.get(friend_id)
        friends.append({'user_id': friend.id, 'username': friend.username, 'email': friend.email})
    return jsonify(friends)
