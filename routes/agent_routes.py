from flask import Blueprint, request, jsonify
from config import OPENAI_CLIENT as client
from services.sql_service import upload_agent_metadata, retrieve_all_agents, delete_agent, update_agent
from services.document_service import upload_files
from functions import get_assistant_session


agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/agent/db/create', methods=['POST'])
def create_agent():
  name = request.json.get('name')
  files = request.files.getlist('file')
  description = request.json.get('description')
  instructions = request.json.get('instructions')
  model = request.json.get('model')
  assistant_session = get_assistant_session()

  if assistant_session is None or not assistant_session:
    return jsonify({'error': 'Invalid assistant session.'}), 400
  if not name or not description or not instructions or not model:
    return jsonify({'error': 'Missing required fields.'})
    
  assistant_id = str(assistant_session['Id'])
  file_ids = None
  
  if files:
    uploaded_files = upload_files(files)
    print(uploaded_files)
  
    stripped_responses = []
    for status, response in uploaded_files:
        response.pop('status', None)
        response.pop('error', None)
        stripped_responses.append(response)
  
    if any(status == 'error' for status, response in uploaded_files):
      return jsonify({
          "message": "Some or all files failed to upload.",
          "details": stripped_responses
      }), 400
  
  
    file_ids = [file['Id'] for file in uploaded_files]

  agent_details = {
    "name": name,
    "system_prompt": instructions,
    "description": description,
    "model": model
  }
  assistant_ids = []
  assistant_ids.append(assistant_id)
  upload = upload_agent_metadata(agent_details, assistant_ids, file_ids)

  if upload is None:
    return jsonify({'error': 'An error occurred while uploading the agent.'}), 400

  return jsonify({
      "message": "Agent added to the database.",
      "data": upload
  }), 200


@agent_bp.route('/agent/db/get_all', methods=['GET'])
def get_all_agents():
  assistant_session = get_assistant_session()
  if not assistant_session:
    return jsonify({'error': 'Invalid assistant session.'}), 401
  agents = retrieve_all_agents()
  if agents is None:
    return jsonify({'error': 'An error occurred while retrieving agents.'}), 400

  return jsonify({"message": "Retrieved agents.", "agents": agents}), 200


@agent_bp.route('/agent/db/delete', methods=['POST'])
def delete_agent_route():
  agent_id = request.json.get('agent_id')
  if not agent_id:
    return jsonify({'error': 'Missing required field: agent_id'}), 400

  deleted_agent_id = delete_agent(agent_id)
  if deleted_agent_id is None:
    return jsonify({'error': 'An error occurred while deleting the agent.'}), 400

  return jsonify({
      "message": "Agent deleted from the database.",
      "agent_id": deleted_agent_id}), 200

@agent_bp.route('/agent/db/update', methods=['POST'])
def update_agent_route():
  agent_id = request.json.get('agent_id')
  name = request.json.get('name')
  files = request.files.getlist('file')
  description = request.json.get('description')
  instructions = request.json.get('instructions')
  model = request.json.get('model')

  if not agent_id or not name and not description and not instructions and not model:
    return jsonify({'error': 'Missing required fields.'}), 400

  update = update_agent(agent_id, name, description, instructions, model)

  if update is None:
    return jsonify({'error': 'An error occurred while updating the agent.'}), 400

  return jsonify({'message': 'Agent updated successfully.', 'agent': update}), 200

