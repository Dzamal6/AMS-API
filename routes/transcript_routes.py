from flask import Blueprint, jsonify, current_app, request
import requests
from services.session_service import check_assistant_session
from config import VOICEFLOW_TRANSCRIPTS
from functions import roles_required

transcript_bp = Blueprint('blueprints', __name__)

@transcript_bp.route('/get_transcripts', methods=['GET'])
@roles_required('admin', 'master', 'worker')
def get_transcripts():
  token = request.cookies.get('assistant_session')
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  endpoint = VOICEFLOW_TRANSCRIPTS + f"/{checksesh['project_id']}"
  headers = {
      'Authorization': f"{checksesh['token']}",
      'accept': 'application/json'
  }
  res = requests.get(endpoint, headers=headers)

  if res.status_code == 200:
    print('Retrieved transcripts.')
    return jsonify({
        'message': 'Retrieved transcripts.',
        'transcripts': res.json()
    }), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    print(f'Failed to retrieve transcripts. {res.status_code}')
    return jsonify({'message': 'Could not retrieve transcripts.'}), 400


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

# @transcript_bp.route('/get_user_transcripts', methods=['GET'])
# def get_user_transcripts(user_id):
#   all_transcripts = get_transcripts();
#   user_transcripts = []
#   if all_transcripts

  
