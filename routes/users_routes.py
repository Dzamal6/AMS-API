# from requests import request
from flask import Blueprint, jsonify, make_response, request

from config import limiter, user_session_serializer
from functions import (
  check_is_current_user,
  check_password,
  get_user_info,
  hash_password,
  login_user,
  roles_required,
)
from services.sql_service import (
  add_user,
  check_user_exists,
  get_all_roles,
  get_all_users,
  get_user,
  register_user,
  remove_user,
  update_user,
)

users_bp = Blueprint('users', __name__)

@users_bp.route('/create_user', methods=['POST'])
@roles_required('admin', 'master')
def create_user_route():
  """
  Creates a new user in the database after checking for a duplicate name.

  URL:
  - POST /create_user

  Parameters:
      email (str): The email of the user to create.
      roles (list of str): The roles assigned to the new user.
      assistants (list of str): IDs of assistants the user will have access to.

  Returns:
      JSON response (dict): A message indicating the success or failure of the creation process.

  Status Codes:
      200 OK: User created successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Either `Admin` or `Master` roles are required to create new users.
  """
  email = request.json.get("email")
  roles = request.json.get("roles")
  modules = request.json.get("modules")
  if not email or not roles:
    return jsonify({'error': 'Missing required fields.'}), 400
  
  exists = check_user_exists(email)
  
  if exists:
    return jsonify({'error': 'User already exists.'}), 400

  if not roles:
    roles = ['Trainee']
  return add_user(email, roles, modules)

@users_bp.route('/register', methods=['POST'])
def register_user_route():
  username = request.json.get('username')
  email = request.json.get('email')
  password = request.json.get('password')
  remember = request.json.get('remember')
  
  if not email or not password:
    return jsonify({'error': 'Missing required fields.'}), 400
  
  exists = check_user_exists(email=email)
  if not exists:
    return jsonify({'error': 'User does not exist.'}), 404
  
  registered_user = register_user(username, email, hash_password(password))
  
  if registered_user is None:
    return jsonify({'error': 'Failed to register user.'}), 400
  
  return login_user(user=registered_user, remember=remember)

@users_bp.route('/delete_user', methods=['POST'])
@roles_required('admin', 'master')
def delete_user_route():
  """
  Deletes a user from the database after verifying that the user is not the current logged-in user.

  URL:
  - POST /delete_user

  Parameters:
      user_id (str): Unique identifier of the user to be deleted.

  Returns:
      JSON response (dict): A message indicating the success or failure of the deletion process.

  Status Codes:
      200 OK: User deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Either `Admin` or `Master` roles are required to delete users.
  """
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
  """
  Updates an existing user in the database based on provided parameters.

  URL:
  - PATCH /update_user

  Parameters:
      user_id (str): Unique identifier of the user to be updated.
      username (str): New username for the user.
      password (str): New password for the user.
      roles (list of str): List of roles assigned to the user.
      assistants (list of str): IDs of assistants accessible to the user.

  Returns:
      JSON response (dict): A message indicating the success or failure of the update process.

  Status Codes:
      200 OK: User updated successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      404 Not Found: No user found with the specified ID.

  Access Control:
      Either `Admin` or `Master` roles are required to update user details.
  """
  data = request.get_json()
  user_id = data['user_id']
  username = data['username']
  roles = data['roles']
  modules = data['modules']
  exists = check_user_exists(id=user_id)
  if not exists:
    return jsonify({'error': 'User does not exist'}), 404

  # password = None if password == '' else hash_password(password)
    
  update = update_user(user_id=user_id, username=username, roles=roles, modules=modules)
  
  if update:
    return jsonify({"message": "User updated successfully", 'user': update}), 200
  else:
    return jsonify({'error': 'Failed to update user.'}), 400
  

@users_bp.route('/login', methods=['POST'])
@limiter.limit('10/minute')
def login_route():
  """
  Logs in a user by validating the provided credentials against the database.

  URL:
  - POST /login

  Parameters:
      credential (str): The email or username of the user attempting to log in.
      password (str): The password of the user attempting to log in.
      remember (bool): Flag to determine if the user should remain logged in for an extended period.

  Returns:
      JSON response (dict): A message indicating the success or failure of the login process,
                            including user details if successful.

  Status Codes:
      200 OK: Login successful.
      401 Unauthorized: Invalid credentials provided.

  Note:
      Uses a `flask limiter` to restrict login attempts to 10 per minute.
  """
  credential = request.json.get("credential")
  password = request.json.get("password")
  remember = request.json.get("remember")
  user = get_user(credential)
  
  if not user or user is None:
    return jsonify({'message': 'Invalid credentials.'}), 401
  if check_password(user['password_hash'], password):
    return login_user(user, remember=remember)
  else:
    return jsonify({'message': 'Invalid credentials.'}), 401


@users_bp.route('/logout', methods=['POST'])
def logout_route():
  """
  Logs out a user by deleting the user session cookie.

  This method does not handle bad request or unauthorized errors directly as these are managed
  by a decorator method.

  URL:
  - POST /logout

  Returns:
      JSON response (dict): A message indicating the success of the logout process.

  Status Codes:
      200 OK: Logout successful.
  """
  response = make_response(jsonify({'message': 'Logout successful'}), 200)
  response.set_cookie('user_session',
                      '',
                      max_age=0,
                      secure=True,
                      httponly=True,
                      samesite='none',
                     )
  response.set_cookie('assistant_session',
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
  """
  Checks if a user session is currently valid by verifying the user session cookie.

  This method does not directly handle bad request or unauthorized errors; these are managed
  by a decorator method applied to the request.

  URL:
  - POST /check_session

  Returns:
      JSON response (dict): Contains a message indicating the validity of the session along with
                            the logged-in user's information, if available.

  Status Codes:
      200 OK: Session valid.
  """
  return jsonify({'message': 'User authenticated', 'user': get_user_info()}), 200 # if get_user_info() throws an error 400 should be returned.

@users_bp.route('/get_all_users', methods=['GET'])
@roles_required('admin', 'master')
def get_users():
  """
  Retrieves all users from the database.

  This endpoint fetches a list of all users.

  URL:
  - GET /get_all_users

  Returns:
      JSON response (dict): A list of users or an error message, depending on the outcome.

  Status Codes:
      200 OK: Users retrieved successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Either `Admin` or `Master` roles are required to obtain users.
  """
  res = get_all_users()
  if res:
    return jsonify({'users': res}), 200
  else:
    return jsonify({'error': 'Could not obtain users.'}), 400

@users_bp.route('/get_all_roles', methods=['GET'])
@roles_required('admin', 'master')
def get_roles():
  """
  Retrieves all roles from the database.

  This endpoint fetches a list of all role entries from the database using the `get_all_roles` method. 

  URL:
  - GET /get_all_roles

  Returns:
      JSON response (dict): 
          - A successful response returns a list of roles (status code 200).
          - An error response returns an error message (status code 400).

  Status Codes:
      200 OK: Roles retrieved successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Either `Admin` or `Master` roles are required to obtain roles.

  Example:
      >>> curl -X GET http://<server>/get_all_roles
      >>> Response: {"roles": ["Admin", "User", "Guest"]}
  """
  res = get_all_roles()
  if res:
    return jsonify({'roles': res}), 200
  else:
    return jsonify({'error': 'Could not obtain roles.'}), 400