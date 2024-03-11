from flask import Blueprint, jsonify, current_app, request, json
import requests
from services.session_service import check_assistant_session
from services.sql_service import get_user_chat_sessions, remove_chat_session 
from services.voiceflow_service import retrieve_transcripts
from config import VOICEFLOW_TRANSCRIPTS
from functions import roles_required, get_user_info, get_assistant_session

transcript_bp = Blueprint('blueprints', __name__)

@transcript_bp.route('/get_transcripts', methods=['GET'])
@roles_required('admin', 'master', 'worker')
def get_transcripts():
  return retrieve_transcripts()


@transcript_bp.route('/update_transcript', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def update_transcript():
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

@transcript_bp.route('/get_user_transcripts', methods=['GET'])
def get_user_transcripts():
  user_info = get_user_info()
  assistant_session = get_assistant_session()

  if not user_info:
    return jsonify({'message': 'Unauthenticated.'}), 401

  if not assistant_session:
    return jsonify({'message': 'Selected assistant could not be resolved.'}), 400
  
  response, status_code = retrieve_transcripts()

  if status_code != 200 or not response.get_json()['transcripts']:
    return jsonify({'message': 'Could not retrieve transcripts.'}), status_code

  user_sessions = get_user_chat_sessions(str(user_info['Id']), str(assistant_session['Id']))

  if user_sessions is None:
    return jsonify({'message': 'Failed to resolve user history.'}), 400
  
  user_transcripts = []
  for transcript in response.get_json()['transcripts']:
    if transcript['sessionID'] in (session['Id'] for session in user_sessions):
      user_transcripts.append(transcript)

  return jsonify({'transcripts': user_transcripts}), 200

@transcript_bp.route('/delete_transcript', methods=['POST'])
def delete_transcript_route():
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

