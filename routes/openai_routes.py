from flask import Blueprint, jsonify, request
from config import OPENAI_CLIENT as client
from services.openai_service import chat_ta, create_agent, delete_agent

openai_bp = Blueprint("openai", __name__)

@openai_bp.route('/openai/initialize', methods=['POST'])
def initialize():
  """
  Initializes an OpenAI assistant (agent) using the specified ID. This is intended for setting up agents
  for specific tasks using the OpenAI assistant API.

  URL:
  - POST /openai/initialize

  Parameters:
      agent_id (str): The ID of the agent to be initialized.

  Returns:
      JSON response (dict): A message indicating successful initialization with a new thread ID and agent ID,
                            or an error message if the agent is not found.

  Status Codes:
      200 OK: Agent initialized successfully.
      404 Not Found: Agent with the specified ID not found.
  """
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
  """
  Deletes an agent from the OpenAI server based on the provided agent ID.

  URL:
  - POST /openai/delete_agent

  Parameters:
      agent_id (str): The ID of the agent to be deleted.

  Returns:
      JSON response (dict): A message indicating whether the agent was deleted successfully or an error occurred.

  Status Codes:
      200 OK: Agent deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.
  """
  agent_id = request.json.get('agent_id')
  print(f"Deleting agent with ID: {agent_id}")
  delete = delete_agent(agent_id)

  if delete is None:
    print(f"(OpenAI) Agent with ID {agent_id} could not be deleted.")
    return jsonify({'error': 'Could not delete agent.'}), 400

  print(f'Agent {agent_id} deleted successfully.')
  return jsonify({'message': 'Agent deleted successfully.'}), 200


@openai_bp.route('/openai/chat', methods=['POST'])
def openai_chat():
  """
  Sends a user message to the specified OpenAI chat assistant and manages the conversation within a given thread.

  URL:
  - POST /openai/chat

  Parameters:
      user_input (str): The message to be sent to the OpenAI assistant.
      agent_id (str): The ID of the agent to use for the conversation.
      thread_id (str): The ID of the thread to use for the conversation, maintaining context across messages.

  Returns:
      JSON response (dict): The chat response from the OpenAI assistant or an error message.

  Status Codes:
      200 OK: Chat response received successfully.
      400 Bad Request: Invalid request payload or an error occurred.
  """
  # authorization_key = request.headers.get('Authorization')
  agent_id = request.json.get('agent_id')
  thread_id = request.json.get('thread_id')
  user_input = request.json.get('message')

  if not agent_id or not thread_id or not user_input:
    print(f"Missing required parameters: agent_id={agent_id}, thread_id={thread_id}, user_input={user_input}")
    return jsonify({'error': 'Missing required fields.'}), 400

  chat = chat_ta(agent_id, thread_id, user_input)

  if 'error' in chat:
    print(f"Error: {chat['error']}")
    return jsonify({'error': chat['error']}), 400

  return jsonify({'message': 'Retrieved response', 'response': chat['success']}), 200


@openai_bp.route('/openai/get_models', methods=['GET'])
def get_models():
  """
  Retrieves a list of currently available models from the OpenAI API, providing users with options for different
  levels of capabilities or specific functionalities.

  URL:
  - GET /openai/get_models

  Returns:
      JSON response (dict): A list of available models or an error message.

  Status Codes:
      200 OK: List of models retrieved successfully.
      400 Bad Request: An error occurred.
  """
  models = client.models.list()

  if not models or models is None:
    return jsonify({'error': 'Could not retrieve models.'}), 400

  return jsonify({'models': [model.id for model in models.data]}), 200

  