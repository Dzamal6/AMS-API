from flask import Blueprint, request, jsonify, make_response
from functions import get_user_info, get_assistant_session, get_chat_session
from services.sql_service import create_chat_session, create_transcript
import services.voiceflow_service as vs
import uuid
from config import chat_session_serializer

voiceflow_bp = Blueprint('voiceflow', __name__)

# needs chat session cookie -> store session id in cookie
@voiceflow_bp.route("/voiceflow/launch", methods=["POST"])
def launch():
  """
  Launches a Voiceflow assistant to initialize a conversation. Validates user and assistant sessions
  before proceeding to create a new chat session.

  URL:
  - POST /voiceflow/launch

  Returns:
      JSON response (dict): The response from the Voiceflow assistant or an error message.

  Status Codes:
      200 OK: Assistant launched successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Raises:
      ValueError: If no user or assistant data is present, indicating a failure to launch.
  """
  user = get_user_info()
  assistant = get_assistant_session()
  
  if not user or not assistant:
    return jsonify({"error": "You need a user and an assistant."}), 400

  print(user, assistant)
  chat_session = create_chat_session(user['Id'], assistant['Id'])
  if not chat_session:
    return jsonify({"error": "Failed to create chat session."}), 400

  chat_session_info = {
    'Id': chat_session['Id']
  }
  
  serializer = chat_session_serializer
  chat_session_data = serializer.dumps(chat_session_info)
  print('chat session token set.')

  if isinstance(chat_session_data, bytes):
    chat_session_data = chat_session_data.decode('utf-8')
  
  response = make_response(jsonify(vs.post_launch_request(chat_session['Id'])), 200)
  response.set_cookie('chat_session', chat_session_data, max_age=None)
    
  return response

@voiceflow_bp.route("/voiceflow/fetch_state", methods=["POST"])
def fetch():
  """
  Fetches the current state of the user from Voiceflow, detailing their position in the conversation flow.

  URL:
  - POST /voiceflow/fetch_state

  Returns:
      JSON response (dict): The current Voiceflow state of the user or an error message.

  Status Codes:
      200 OK: State retrieved successfully.
      400 Bad Request: No user cookie set or an error occurred.
  """
  user = get_user_info()
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.fetch_state(user['Id'])), 200

@voiceflow_bp.route("/voiceflow/delete_state", methods=["DELETE"])
def delete():
  """
  Deletes the user's current state in Voiceflow.

  URL:
  - DELETE /voiceflow/delete_state

  Returns:
      JSON response (dict): A confirmation of deletion or an error message.

  Status Codes:
      200 OK: State deleted successfully.
      400 Bad Request: No user cookie set or an error occurred.
  """
  user = get_user_info()
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.delete_state(user)), 200

@voiceflow_bp.route('/voiceflow/interact', methods=["POST"])
def interact():
  """
  Facilitates interaction with a Voiceflow assistant using user-provided inputs such as button clicks or text messages.

  URL:
  - POST /voiceflow/interact

  Parameters:
      btn (object): The button clicked by the user, if applicable.
      response (str): The text message sent by the user to the assistant.

  Returns:
      JSON response (dict): The response from the Voiceflow assistant or an error message.

  Status Codes:
      200 OK: Interaction completed successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: Assistant or User session could not be resolved.
  """
  user = get_user_info()
  response = request.json.get("text", None)
  btn = request.json.get("btn", None)
  chat_session = get_chat_session()

  if not user:
    return jsonify({"message": "Unauthorized"}), 401

  if btn is None and response is None:
    return jsonify({"error": "No sufficient response was provided."}), 400

  if not chat_session:
    return jsonify({'error': "Failed to resolve session."}), 400

  if btn:
    return jsonify(vs.post_button(chat_session['Id'], btn)), 200
  else:
    return jsonify(vs.post_text(chat_session['Id'], response)), 200

@voiceflow_bp.route("/voiceflow/update_variable", methods=["PATCH"])
def update_variable():
  """
  Updates a variable within the Voiceflow assistant's session context based on user input.

  URL:
  - PATCH /voiceflow/update_variable

  Parameters:
      key (str): The name of the variable to update.
      value (str): The new value for the variable.

  Returns:
      JSON response (dict): Confirmation of the variable update or an error message.

  Status Codes:
      200 OK: Variable updated successfully.
      400 Bad Request: Invalid request payload or an error occurred.
  """
  user = get_user_info()
  key = request.json.get("key", None)
  value = request.json.get("value", None)

  if not key or not value:
    return jsonify({"error": "You need a key and a value"}), 400
  
  if user:
    return jsonify({"message": vs.update_variable(user['Id'], key, value)}), 200
  else:
    return jsonify({"error": "user is needed"}), 400

@voiceflow_bp.route("/voiceflow/create-transcript", methods=["PUT"])
def transcript():
  """
  Creates a transcript of a Voiceflow conversation, storing details in both Voiceflow and the local database.

  URL:
  - PUT /voiceflow/create-transcript

  Parameters:
      device (str): The device on which the conversation occurred.
      oss (str): The operating system of the device.
      browser (str): The browser used during the conversation.

  Returns:
      JSON response (dict): Confirmation of transcript creation or an error message.

  Status Codes:
      200 OK: Transcript created successfully.
      400 Bad Request: Invalid request payload or an error occurred.
  """
  user = get_user_info()
  assistant_session = get_assistant_session()
  device = request.json.get('device', None)
  oss = request.json.get('os', None)
  browser = request.json.get('browser', None)
  chat_session = get_chat_session()

  if not assistant_session:
    return jsonify({'error': "Failed to resolve assistant session"}), 400
  
  if not user:
    return jsonify({"error": "Failed to resolve user session"}), 400

  if not chat_session:
    return jsonify({'error': "Failed to resolve chat session."})

  create = vs.create_transcript(chat_session['Id'], assistant_session['project_id'], device, oss, browser)

  print(f"Create: {create}")

  if create.get('message') and create['message'] == 'Unauthorized':
    return jsonify({'error': create}), 400

  sql_create = create_transcript(create['_id'], create['sessionID'], user['Id'], user['Username'])

  if not sql_create:
    return jsonify({'error': "Failed to create transcript in Database"}), 400
    # Delete transcript from VF and retry action until it succeeds
    
  return create, 200