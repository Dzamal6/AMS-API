from flask import Blueprint, request, jsonify
from config import OPENAI_CLIENT as client
from services.sql_service import upload_agent_metadata, retrieve_all_agents, delete_agent, update_agent, upload_files
from functions import get_assistant_session


agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/agent/db/create', methods=['POST'])
def create_agent():
  """
  Creates a new agent in the database along with any associated files. If files already exist,
  they are linked to the new agent rather than duplicated.

  URL:
  - POST /agent/db/create

  Parameters:
      name (str): The name of the new agent.
      files (list of FileStorage): A list of files to be uploaded.
      description (str): A description of the agent, for management purposes.
      instructions (str): Instructions defining the agent's behavior and presentation.
      model (str): The OpenAI model to use for the agent.

  Returns:
      JSON response (dict): The created agent object along with a status message or an error message.

  Status Codes:
      200 OK: Agent created successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Notes:
      - Assistant session must be established before calling this method.
      - `upload_files` and `upload_agent_metadata` methods are used to handle file and metadata uploading.
  """
  name = request.form.get('name')
  files = request.files.getlist('file')
  # file_ids = request.form.getlist('file_ids')
  description = request.form.get('description')
  instructions = request.form.get('instructions')
  model = request.form.get('model')
  assistant_session = get_assistant_session()

  print(files)

  if assistant_session is None or not assistant_session:
    return jsonify({'error': 'Invalid assistant session.'}), 400
  if not name or not description or not instructions or not model:
    return jsonify({'error': 'Missing required fields.'}), 400
    
  assistant_id = str(assistant_session['Id'])
  
  # if not file_ids:
  file_ids = []
  
  if files:
    assistant_ids = []
    assistant_ids.append(assistant_id)
    uploaded_files = upload_files(files, assistant_ids)
    print(uploaded_files)
  
    for status, response in uploaded_files:
      if status == 'success' and response['Id'] not in file_ids:
        file_ids.append(response['Id'])
        
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
  """
  Retrieves all agents from the database. Requires an established assistant session.

  URL:
  - GET /agent/db/get_all

  Returns:
      JSON response (dict): A list of retrieved agents or an error message.

  Status Codes:
      200 OK: All agents retrieved successfully.
      400 Bad Request: An error occurred.
      401 Unauthorized: No assistant session was established.

  Notes:
      - Calls `retrieve_all_agents` to fetch all agents from the database.
  """
  assistant_session = get_assistant_session()
  if not assistant_session:
    print("No assistant selected.")
    return jsonify({'error': 'Invalid assistant session.'}), 401
  agents = retrieve_all_agents(assistant_session['Id'])
  if agents is None:
    return jsonify({'error': 'An error occurred while retrieving agents.'}), 400

  return jsonify({"message": "Retrieved agents.", "agents": agents}), 200


@agent_bp.route('/agent/db/delete', methods=['POST'])
def delete_agent_route():
  """
  Deletes a specified agent from the database based on the agent's ID.

  URL:
  - POST /agent/db/delete

  Parameters:
      agent_id (str): The ID of the agent to be deleted.

  Returns:
      JSON response (dict): A message indicating the deletion status and details of the deleted agent or an error message.

  Status Codes:
      200 OK: Agent deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Notes:
      - Calls `delete_agent` method to remove the agent from the database.
  """
  agent_id = request.json.get('agent_id')
  if not agent_id:
    return jsonify({'error': 'Missing required field: agent_id'}), 400

  deleted_agent_id = delete_agent(agent_id)
  if deleted_agent_id is None:
    return jsonify({'error': 'An error occurred while deleting the agent.'}), 400

  return jsonify({
      "message": "Agent deleted from the database.",
      "agent_id": deleted_agent_id}), 200

@agent_bp.route('/agent/db/update', methods=['POST']) # ADDING DUPLICATE FILES TO EXISTING OR NEW AGENTS DOESN'T ADD THEM
def update_agent_route():
  """
  Updates an existing agent in the database, including uploading new files without duplicating existing ones.

  URL:
  - POST /agent/db/update

  Parameters:
      agent_id (str): The ID of the agent to be updated.
      name (str): The new name of the agent.
      description (str): The new description of the agent.
      instructions (str): The new instructions for the agent.
      model (str): The new OpenAI model to use for the agent.
      files (list of FileStorage): New files to be uploaded.
      file_ids (list of str): Updated list of file IDs associated with the agent.

  Returns:
      JSON response (dict): A message indicating the update status of the agent along with updated agent details or an error message.

  Status Codes:
      200 OK: Agent updated successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: No assistant session was established.

  Notes:
      - Calls `update_agent` to update agent details and `upload_files` for new file uploads.
  """
  agent_id = request.form.get('agent_id')
  name = request.form.get('name')
  files = request.files.getlist('file')
  file_ids = request.form.getlist('file_ids')
  description = request.form.get('description')
  instructions = request.form.get('instructions')
  model = request.form.get('model')

  assistant_session = get_assistant_session()

  if assistant_session is None or not assistant_session:
    return jsonify({'error': 'Invalid assistant session.'}), 400
  
  assistant_id = str(assistant_session['Id'])

  if not agent_id or not name and not description and not instructions and not model:
    return jsonify({'error': 'Missing required fields.'}), 400
  print(f'Received file ids: {[f"{file_id}" for file_id in file_ids]}')
  if not file_ids:
    file_ids = []

  if files:
    assistant_ids = []
    assistant_ids.append(assistant_id)
    uploaded_files = upload_files(files)
    print(f'UPLOADED FILES: {uploaded_files}')

    for status, response in uploaded_files:
      if status == 'success' and response['Id'] not in file_ids:
        file_ids.append(response['Id'])
  print(f'Updating agent with files: {[f"{file_id}, " for file_id in file_ids]}')
  update = update_agent(agent_id, name, description, instructions, model, file_ids)

  if update is None:
    return jsonify({'error': 'An error occurred while updating the agent.'}), 400

  return jsonify({'message': 'Agent updated successfully.', 'agent': update}), 200

