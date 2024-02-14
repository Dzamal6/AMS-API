# from requests import request
from functions import encrypted_str, roles_required, check_is_current_user, get_user_info
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import Blueprint, jsonify, make_response, current_app, request
from services.airtable_service import check_user_exists, add_user, remove_user, login_user, get_all_users, get_all_roles, get_user_roles, update_user
from config import user_session_serializer

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
  return add_user(username, encrypted_str(password), roles, assistants)

# check if user is deleting self
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
  if not check_user_exists(username):
    return jsonify({'error': 'User does not exist'}), 404
  update = update_user(user_id, username, password, roles, assistants)
  if update:
    return jsonify({"message": "User updated successfully", 'user': update}), 200
  else:
    return jsonify({'error': 'Failed to update user.'}), 400
  


@users_bp.route('/login', methods=['POST'])
def login_route():
  data = request.get_json()
  username = data['username']
  password = data['password']
  remember = data['remember']
  login = login_user(username, encrypted_str(password))
  if login['status'] == 200:
    user_roles = get_user_roles(login['user']['fields']['Roles'])
    serializer = user_session_serializer
    user_info = {
        'Username': username,
        'Id': login['user']['id'],
        'Roles': user_roles,
        'Assistants':  login['user']['fields']['Assistants'],
        'Created': login['user']['fields']['Created'],
        'LastModified': login['user']['fields']['LastModified'],
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
                        max_age=604800 if remember else None) # NOT WORKING CORRECTLY
    return response
  else:
    return jsonify({'message': 'Invalid username or password'}), 401


@users_bp.route('/logout', methods=['POST'])
def logout_route():
  response = make_response(jsonify({'message': 'Logout successful'}), 200)
  response.set_cookie('user_session',
                      '',
                      expires=0,
                      httponly=True,
                      secure=True,
                      samesite='None')
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
