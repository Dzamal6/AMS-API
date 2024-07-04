from flask import Blueprint, jsonify, current_app, request, json
import requests
from services.session_service import check_assistant_session
from services.sql_service import get_user_chat_sessions, remove_chat_session 
from config import VOICEFLOW_TRANSCRIPTS
from functions import roles_required, get_user_info, get_module_session

transcript_bp = Blueprint('blueprints', __name__)

# @transcript_bp.route('/get_transcripts', methods=['GET'])
# @roles_required('admin', 'master', 'worker')
# def get_transcripts():
#   """
#   Serves as a conduit to retrieve all transcripts associated with the assistant from the Voiceflow database.

#   URL:
#   - GET /get_transcripts

#   Returns:
#       JSON response (dict): A list of transcripts or an error message.

#   Status Codes:
#       200 OK: List of transcripts retrieved successfully.
#       400 Bad Request: An error occurred.
#       401 Unauthorized: Assistant session could not be resolved.

#   Notes:
#       This endpoint primarily acts as a middleman utilizing the `retrieve_transcripts` method
#       which is shared across several endpoints to standardize transcript retrieval.

#   Access Control:
#       Requires `Admin`, `Master`, or `Worker` roles to retrieve transcripts.
#   """
#   return retrieve_transcripts()


@transcript_bp.route('/update_transcript', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def update_transcript():
  """
  Updates specific fields of a transcript in the Voiceflow database based on provided data.

  URL:
  - POST /update_transcript

  Parameters:
      data (dict): Key-value pairs representing the fields to be updated in the transcript.

  Returns:
      JSON response (dict): A message indicating the success of the update.

  Status Codes:
      200 OK: Transcript updated successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: Assistant session could not be resolved.

  Access Control:
      Requires `Admin`, `Master`, or `Worker` roles to execute.
  """
  token = request.cookies.get('assistant_session')
  # transcript_id = request.json.get('transcript_id')
  data = request.json.get('data')
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  payload = {'data': {}}
  for key, value in data.items():
    if value is not None and value != "":
      payload['data'][key] = value

  headers = {
      'Auhorization': f"{checksesh['token']}",
      'accept': 'transcript_bplication/json',
      'Content-Type': 'application/json'
  }
  endpoint = VOICEFLOW_TRANSCRIPTS + f"/{checksesh['project_id']}/{data['_id']}"

  response = requests.patch(endpoint, json=payload, headers=headers)
  if response.status_code == 200:
    return jsonify({'message': 'Transcript updated.'}), 200
  elif response.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    return jsonify({'message': 'Transcript update failed.'}), 400


@transcript_bp.route('/get_transcript_dialog', methods=['POST'])
def get_transcript_dialog():
  """
  Retrieves dialog details from a specific transcript stored in the Voiceflow database.

  URL:
  - POST /get_transcript_dialog

  Parameters:
      transcript_id (str): The ID of the transcript from which to retrieve the dialog.

  Returns:
      JSON response (dict): The dialog object from the specified transcript or an error message.

  Status Codes:
      200 OK: Transcript dialog retrieved successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: Assistant session could not be resolved.
  """
  token = request.cookies.get('assistant_session')
  transcript_id = request.json.get('transcript_id')
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  endpoint = VOICEFLOW_TRANSCRIPTS + f"/{checksesh['project_id']}/{transcript_id}"
  headers = {
      'Authorization': f"{checksesh['token']}",
      'accept': 'application/json'
  }
  response = requests.get(endpoint, headers=headers)

  if response.status_code == 200:
    return jsonify({
        'message': 'Retrieved transcript.',
        'transcript': response.json()
    }), 200
  elif response.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    return jsonify({'message': 'Transcript retrieval failed.'}), 400

# @transcript_bp.route('/get_user_transcripts', methods=['GET'])
# def get_user_transcripts():
#   """
#   Retrieves all transcripts related to a user and their selected assistant from the Voiceflow database.

#   URL:
#   - GET /get_user_transcripts

#   Returns:
#       JSON response (dict): A list of transcripts or an error message.

#   Status Codes:
#       200 OK: List of transcripts retrieved successfully.
#       400 Bad Request: Assistant could not be resolved or an error occurred.
#       401 Unauthorized: User session could not be resolved.

#   Notes:
#       Transcripts are fetched based on the user and assistant sessions retrieved from cookies. 
#       The list is then filtered to include only those relevant to the current user.
#   """
#   user_info = get_user_info()
#   module_session = get_module_session()

#   if not user_info:
#     return jsonify({'message': 'Unauthenticated.'}), 401

#   if not module_session:
#     return jsonify({'message': 'Selected assistant could not be resolved.'}), 400
  
#   # response, status_code = retrieve_transcripts()

#   if status_code != 200 or not response.get_json()['transcripts']:
#     return jsonify({'message': 'Could not retrieve transcripts.'}), status_code

#   user_sessions = get_user_chat_sessions(str(user_info['Id']), str(module_session['Id']))

#   if user_sessions is None:
#     return jsonify({'message': 'Failed to resolve user history.'}), 400
  
#   user_transcripts = []
#   for transcript in response.get_json()['transcripts']:
#     if transcript['sessionID'] in (session['Id'] for session in user_sessions):
#       user_transcripts.append(transcript)

#   return jsonify({'transcripts': user_transcripts}), 200

@transcript_bp.route('/delete_transcript', methods=['POST'])
def delete_transcript_route():
  """
  Deletes a transcript and its associated metadata from both the Voiceflow and the API's internal databases.

  URL:
  - POST /delete_transcript

  Parameters:
      transcript_id (str): The ID of the transcript to delete.
      session_id (str): The ID of the session associated with the transcript.

  Returns:
      JSON response (dict): A message indicating the success of the deletion and the ID of the deleted transcript.

  Status Codes:
      200 OK: Transcript deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: Assistant session could not be resolved.

  Notes:
      The deletion process involves removing the transcript from the API's database using `remove_chat_session`
      method followed by its removal from the Voiceflow database.
  """
  token = request.cookies.get('assistant_session')
  transcript_id = request.json.get('transcript_id')
  session_id = request.json.get('session_id')
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  remove_session = remove_chat_session(session_id)
  # Transcript is automatically cascade deleted from db on session deletion

  if not remove_session:
    return jsonify({'error': "Failed to remove session."}), 400
  
  headers = {
      'Authorization': f"{checksesh['token']}",
  }

  endpoint = VOICEFLOW_TRANSCRIPTS + f"/{checksesh['project_id']}/{transcript_id}"

  res = requests.delete(endpoint, headers=headers)
    
  if res.status_code == 200:
    return jsonify({
        'message': 'Deleted transcript.',
        'transcript': res.json()
    }), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    return jsonify({'message': 'Failed to delete transcript'}), 400

