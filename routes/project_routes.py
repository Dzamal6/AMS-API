from flask import Blueprint, request, jsonify, make_response, current_app
import requests
from functions import decrypt_token, encrypt_token, roles_required, check_assistant_permission
from services.airtable_service import add_assistant, delete_assistant, get_all_assistants
from config import AIRTABLE_ENDPOINT, HEADERS, FERNET_KEY, assistant_session_serializer

project_bp = Blueprint('project', __name__)

@project_bp.route('/set_project', methods=['POST'])
def set_project():
  project_id = request.json.get('project_id')
  
  if not check_assistant_permission(project_id):
    return jsonify({'error': 'User does not have access to this project.'}), 401
    
  print(f'Fetching: {AIRTABLE_ENDPOINT}/{project_id}')
  response = requests.get(f'{AIRTABLE_ENDPOINT}/{project_id}', headers=HEADERS)
  responseJSON = response.json()

  if response.status_code == 200 and responseJSON['fields']:
    Tok = decrypt_token(FERNET_KEY, responseJSON['fields']['token'])
    serializer = assistant_session_serializer
    token = serializer.dumps({
        'token': Tok,
        'project_id': responseJSON['fields']['projectId']
    })
    print('Assistant session token set.')

    if isinstance(token, bytes):
      token = token.decode('utf-8')

    response = make_response(
        jsonify({
            'message': 'Connection was successful.',
            'assistant': {'Name': responseJSON['fields']['name'],
                          'Id': responseJSON['id'],
                          'Created': responseJSON['fields']['Created'],
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
                    "Connection was unsuccessful."}), response.status_code


@project_bp.route('/get_projects', methods=['GET'])
def get_projects():
  # Old code
  # query = '?fields%5B%5D=name&fields%5B%5D=Created'
  # response = requests.get(AIRTABLE_ENDPOINT + query, headers=HEADERS)
  # if response.status_code == 200 and response.json()['records']:
  #   return jsonify({
  #       'message': 'Connection was successful.',
  #       'records': response.json()['records']
  #   })
  # elif response.status_code == 200:
  #   return jsonify({'message': 'There are no records in the database.'}), 200
  # else:
  #   return jsonify({'message': 'Could not obtain records.'}), 400
  # New code
  projects = get_all_assistants()
  if projects: 
    return jsonify({
        'message': 'Connection was successful.',
        'assistants': projects
    })
  else:
    return jsonify({'message': 'Could not obtain assistants.'}), 400
  

@project_bp.route('/add_project', methods=['POST'])
@roles_required('admin')
def add_project():
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
    if res:
      return jsonify({
          'message': 'Project added to Airtable.',
          'data': {
              'name': response.json()['project']['name'],
              'id': res if not None else 'none',
          }
      })
    else:
      return jsonify({'message': 'Could not add project.'}), 400
  else:
    return jsonify({'message':
                    'No project exists with this information.'}), 400


@project_bp.route('/delete_project', methods=['POST'])
@roles_required('admin')
def delete_project():
  project_name = request.json.get('project_name')
  res = delete_assistant(project_name)
  if res:
    return jsonify({'message': 'Project deleted from Airtable.'}), 200
  else:
    return jsonify({'message': 'Could not delete project.'}), 400
