from flask import Blueprint, jsonify, request, current_app
import requests
from services.session_service import check_assistant_session
from config import VOICEFLOW_KNOWLEDGE_BASE
from functions import roles_required

knowledge_bp = Blueprint('knowledge', __name__)

@knowledge_bp.route('/get_document_list', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def get_document_list():
  token = request.cookies.get('assistant_session')
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  headers = {'Authorization': f"{checksesh['token']}"}

  print(f"getting response from {VOICEFLOW_KNOWLEDGE_BASE}")
  response = requests.get(VOICEFLOW_KNOWLEDGE_BASE + '?limit=100',
                          headers=headers)

  if response.status_code == 200:
    return response.json(), 200
  else:
    print(f"returned {response.status_code}")
    return jsonify({'message': 'Could not obtain documents.'}), 400


@knowledge_bp.route('/upload_url', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def upload_url():
  name = request.json.get('name')
  url = request.json.get('document_url')
  token = request.cookies.get('assistant_session')
  endpoint = VOICEFLOW_KNOWLEDGE_BASE + '/upload?maxChunkSize=1000'
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  headers = {
      'Authorization': checksesh['token'],
      'Accept': 'application/json',
      'content-type': 'application/json; charset=utf-8'
  }
  res = requests.post(endpoint,
                      json={'data': {
                          'name': name,
                          'type': 'url',
                          'url': url
                      }},
                      headers=headers)

  if res.status_code == 200:
    print(res.json())
    return jsonify({
        'message': 'Upload successful.',
        'document': res.json()['data']
    }), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    print(res.json())
    return jsonify({'message': 'Upload failed.'}), 400


@knowledge_bp.route('/delete_document', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def delete_document():
  id = request.json.get('document_id')
  token = request.cookies.get('assistant_session')
  endpoint = VOICEFLOW_KNOWLEDGE_BASE + f'/{id}'
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  headers = {'Authorization': f"{checksesh['token']}"}
  res = requests.delete(endpoint, headers=headers)

  if res.status_code == 200:
    return jsonify({'message': 'Document deleted.'}), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    return jsonify({'error': "Failed to delete document."}), 400


@knowledge_bp.route('/get_document_chunks', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def get_document_chunks():
  id = request.json.get('document_id')
  token = request.cookies.get('assistant_session')
  endpoint = VOICEFLOW_KNOWLEDGE_BASE + f'/{id}'
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  headers = {
      'Authorization': f"{checksesh['token']}",
      'Accept': 'application/json'
  }
  res = requests.get(endpoint, headers=headers)

  if res.status_code == 200:
    return jsonify({'message': 'Chunks retrieved', 'data': res.json()}), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    return jsonify({'error': "Failed to fetch chunks"}), 400


@knowledge_bp.route('/upload_document', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def upload_document():
  token = request.cookies.get('assistant_session')
  endpoint = VOICEFLOW_KNOWLEDGE_BASE + '/upload?maxChunkSize=1000'
  file = request.files['file']
  checksesh = check_assistant_session(current_app, token)
  if not checksesh:
    return jsonify({'error': "Invalid or expired session data."}), 401

  headers = {
      'Authorization': f"{checksesh['token']}",
      'accept': 'multipart/form-data'
  }
  res = requests.post(endpoint,
                      files={
                          'file': (file.filename, file.stream,
                                   file.content_type, file.headers)
                      },
                      headers=headers)
  print(f'response: {res.json()}')
  if res.status_code == 200:
    print(f'Upload success. {res.json()["data"]}')
    return jsonify({
        'message': 'Upload successful.',
        'document': res.json()['data']
    }), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    print(f'Upload failed. {res.status_code}')
    return jsonify({'message': 'Upload failed.'}), 400
