from flask import Blueprint, jsonify, request
from config import OPENAI_CLIENT as client
from services.openai_service import chat_ta, create_agent, delete_agent

openai_bp = Blueprint("openai", __name__)

@openai_bp.route('/openai/initialize', methods=['POST'])
def initialize():
  agent_id = request.json.get('agent_id')
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")

  new_agent_id = create_agent(agent_id)

  if not new_agent_id or new_agent_id is None:
    return jsonify({'error': 'Agent not found'}), 404

  return jsonify({'thread_id': thread.id, 'agent_id': new_agent_id}), 200


@openai_bp.route('/openai/delete_agent', methods=['POST'])
def delete_agent_route():
  agent_id = request.json.get('agent_id')
  print(f"Deleting assistant with ID: {agent_id}")
  delete = delete_agent(agent_id)

  if delete is None:
    print(f"Agent with ID {agent_id} could not be deleted.")
    return jsonify({'error': 'Could not delete agent.'}), 400

  print(f'Agent {agent_id} deleted successfully.')
  return jsonify({'message': 'Agent deleted successfully.'}), 200


@openai_bp.route('/openai/chat', methods=['POST'])
def openai_chat():
  # authorization_key = request.headers.get('Authorization')
  agent_id = request.json.get('agent_id')
  thread_id = request.json.get('thread_id')
  user_input = request.json.get('message')

  if not agent_id or not thread_id or not user_input:
    return jsonify({'error': 'Missing required fields.'}), 400

  chat = chat_ta(agent_id, thread_id, user_input)

  if 'error' in chat:
    return jsonify({'error': chat['error']}), 400

  return jsonify({'message': 'Retrieved response', 'response': chat['success']}), 200

  