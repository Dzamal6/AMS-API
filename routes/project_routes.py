from flask import Blueprint, request, jsonify, make_response, current_app
import requests
from functions import decrypt_token, encrypt_token, roles_required, check_assistant_permission, get_user_info, check_user_projects, check_admin
from services.sql_service import add_assistant, delete_assistant, get_all_assistants, get_assistant_by_id
from config import FERNET_KEY, assistant_session_serializer

project_bp = Blueprint('project', __name__)

@project_bp.route('/set_project', methods=['POST'])
def set_project():
  """
  Sets up a session for a specified Voiceflow assistant if the user is authorized, 
  and stores relevant session data in a cookie.

  URL:
  - POST /set_project

  Parameters:
      project_id (str): The ID of the Voiceflow assistant for which the session is to be set up.

  Returns:
      JSON response (dict): A message indicating the success of the setup, along with assistant details
                            such as `Name`, `Id`, and `Created`, or an error message.

  Status Codes:
      200 OK: Project set successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: User is not allowed to access the specified Voiceflow assistant.
  """
  project_id = request.json.get('project_id')
  
  if not check_assistant_permission(project_id):
    return jsonify({'error': 'User does not have access to this project.'}), 401
    
  assistant = get_assistant_by_id(project_id)
  
  if assistant is not None and isinstance(assistant, dict):
    Tok = decrypt_token(FERNET_KEY, assistant['Token']) # API token should be encrypted in the cookie and decrypted only when using it.
    serializer = assistant_session_serializer
    token = serializer.dumps({
        'token': Tok,
        'project_id': assistant['ProjectId'],
        'version_id': assistant['VersionId'],
        'Id': str(assistant['Id'])
    })
    print('Assistant session token set.')

    if isinstance(token, bytes):
      token = token.decode('utf-8')

    response = make_response(
        jsonify({
            'message': 'Connection was successful.',
            'assistant': {'Name': assistant['Name'],
                          'Id': str(assistant['Id']),
                          'Created': assistant['Created'],
                         }
        }), 200)
    response.set_cookie('assistant_session',
                        token,
                        httponly=True,
                        secure=True,
                        samesite='none')
    return response
  else:
    return jsonify({'message':
                    "Connection was unsuccessful."}), 400


@project_bp.route('/get_projects', methods=['GET'])
def get_projects():
  """
  Retrieves a list of all the Voiceflow assistants that the user has access to from the database.

  URL:
  - GET /get_projects

  Returns:
      JSON response (dict): A list of assistants or an error message.

  Status Codes:
      200 OK: List of projects retrieved successfully.
      400 Bad Request: Assistants could not be retrieved.
      401 Unauthorized: User is not authenticated.
      404 Not Found: No assistants found.

  Notes:
      User authentication is verified using the `get_user_info` function.
      The function checks if the user is an admin using the `check_admin` function.
  """
  projects = get_all_assistants()
  user_session = get_user_info()
  if not user_session: # <-- Likely redundant since before_request method already checks for this.
    return jsonify({'message': 'User is not authenticated.'}), 401

  if check_admin():
    return jsonify({'assistants': projects}), 200
    
  projects = check_user_projects(projects, user_session['Assistants'])
  
  if projects:
    return jsonify({
        'message': 'Connection was successful.',
        'assistants': projects
    }), 200
  else:
    if len(projects) == 0:
      return jsonify({'message': "No assistants found."}), 404
    else:
      return jsonify({'message': 'Could not obtain assistants.'}), 400
  

@project_bp.route('/add_project', methods=['POST'])
@roles_required('admin')
def add_project():
  """
  Adds a Voiceflow assistant's metadata to the database after retrieving and encrypting necessary data.

  URL:
  - POST /add_project

  Parameters:
      version_id (str): The version ID of the Voiceflow assistant to add.
      token (str): The API key of the Voiceflow assistant, which will be encrypted and stored.

  Returns:
      JSON response (dict): A message indicating whether the assistant was added successfully,
                            along with the assistant `Name`, `Id`, and `Created` properties, or an error message.

  Status Codes:
      200 OK: Project added successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: User is not allowed to add assistants.

  Note for use:
      The assistant must be previously configured in Voiceflow Studio. The `version_id` is used for specific Voiceflow endpoints.
      This endpoint requires an `Admin` role to execute.
  """
  version_id = request.json.get('version_id')
  token = request.json.get('token')
  endpoint = f'https://api.voiceflow.com/v2/versions/{version_id}/export'
  headers = {'Authorization': f'{token}', 'accept': 'application/json'}
  response = requests.get(endpoint, headers=headers)
  encrypted_token = encrypt_token(FERNET_KEY, token)

  if response.status_code == 200:
    res = add_assistant(encrypted_token,
                        response.json()['project']['name'], version_id,
                        response.json()['project']['_id'])
    return res
  else:
    return jsonify({'message':
                    'No project exists with this information or an error occurred while adding the project.'}), 400


@project_bp.route('/delete_project', methods=['POST'])
@roles_required('admin')
def delete_project():
  """
  Deletes a specified Voiceflow assistant from the API's internal database but does not affect Voiceflow's records.

  URL:
  - POST /delete_project

  Parameters:
      project_name (str): The name of the Voiceflow assistant to delete.

  Returns:
      JSON response (dict): A message indicating whether the assistant was deleted successfully.

  Status Codes:
      200 OK: Project deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Requires the `Admin` role for deleting assistants.
  """
  project_name = request.json.get('project_name') # TODO: change this to ID as this poses a likely conflict.
  res = delete_assistant(project_name)
  if res:
    return jsonify({'message': 'Project deleted from the database.'}), 200
  else:
    return jsonify({'message': 'Could not delete project.'}), 400
