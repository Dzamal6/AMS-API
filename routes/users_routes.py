# from requests import request
from flask import Blueprint, jsonify, make_response, request

from config import limiter, user_session_serializer
from functions import (
  check_is_current_user,
  check_password,
  get_user_info,
  hash_password,
  roles_required,
)
from services.sql_service import (
  add_user,
  check_user_exists,
  get_all_roles,
  get_all_users,
  get_user,
  remove_user,
  update_user,
)

users_bp = Blueprint('users', __name__)

@users_bp.route('/create_user', methods=['POST'])
@roles_required('admin', 'master')
def create_user_route():
  data = request.get_json()
  username = data['username']
  password = data['password']
  roles = data['roles']
  assistants = data['assistants']
  exists = check_user_exists(username)
  
  if exists:
    return jsonify({'error': 'User already exists'}), 400

  if not roles:
    roles = ['Trainee']
  return add_user(username, hash_password(password), roles, assistants)

@users_bp.route('/delete_user', methods=['POST'])
@roles_required('admin', 'master')
def delete_user_route():
  data = request.get_json()
  user_id = data['user_id']
  is_current_user = check_is_current_user(user_id)
  
  if is_current_user:
    return jsonify({'error': 'Cannot delete self'}), 400
  remove = remove_user(user_id)
  if remove:
    return remove
  else:
    return jsonify({'error': 'Failed to remove user.'}), 400


@users_bp.route('/update_user', methods=['PATCH'])
@roles_required('admin', 'master')
def update_user_route():
  data = request.get_json()
  user_id = data['user_id']
  username = data['username']
  password = data['password']
  roles = data['roles']
  assistants = data['assistants']
  if not check_user_exists(user_id):
    return jsonify({'error': 'User does not exist'}), 404

  password = None if password == '' else hash_password(password)
    
  update = update_user(user_id, username, password, roles, assistants)
  
  if update:
    return jsonify({"message": "User updated successfully", 'user': update}), 200
  else:
    return jsonify({'error': 'Failed to update user.'}), 400
  

@users_bp.route('/login', methods=['POST'])
@limiter.limit('10/minute')
def login_route():
  data = request.get_json()
  username = data['username']
  password = data['password']
  remember = data['remember']
  user = get_user(username)
  
  if not user:
    return jsonify({'message': 'Invalid credentials.'}), 401
  if check_password(user['password_hash'], password):
    serializer = user_session_serializer
    user_info = {
        'Username': username,
        'Id': user['Id'],
        'Roles': user['Roles'],
        'Assistants':  user['Assistants'],
        'Created': user['Created'],
        'LastModified': user['LastModified'],
    }
    session_data = serializer.dumps(user_info)
    print('user session token set.')

    if isinstance(session_data, bytes):
      session_data = session_data.decode('utf-8')

    response = make_response(jsonify({'message': 'Login successful', 'user': user_info}), 200)
    response.set_cookie('user_session',
                        session_data,
                        httponly=True,
                        secure=True,
                        samesite='none',
                        max_age=None if not remember else 1209600)
    return response
  else:
    return jsonify({'message': 'Invalid credentials.'}), 401


@users_bp.route('/logout', methods=['POST'])
def logout_route():
  response = make_response(jsonify({'message': 'Logout successful'}), 200)
  response.set_cookie('user_session',
                      '',
                      max_age=0,
                      secure=True,
                      httponly=True,
                      samesite='none',
                     )
  response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  response.headers["Pragma"] = "no-cache"
  response.headers["Expires"] = "0"

  return response


@users_bp.route('/check_session', methods=['POST'])
def check_session_route():
  return jsonify({'message': 'User authenticated', 'user': get_user_info()}), 200

@users_bp.route('/get_all_users', methods=['GET'])
@roles_required('admin', 'master')
def get_users():
  res = get_all_users()
  if res:
    return jsonify({'users': res}), 200
  else:
    return jsonify({'error': 'Could not obtain users.'}), 400

@users_bp.route('/get_all_roles', methods=['GET'])
@roles_required('admin', 'master')
def get_roles():
  res = get_all_roles()
  if res:
    return jsonify({'roles': res}), 200
  else:
    return jsonify({'error': 'Could not obtain roles.'}), 400