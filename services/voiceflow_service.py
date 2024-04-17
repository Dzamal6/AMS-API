from flask_cors import version
import requests
from flask import jsonify, current_app, request
from config import VOICEFLOW_TRANSCRIPTS
from services.session_service import check_assistant_session
from services.sql_service import get_all_chat_sessions, get_all_transcripts
from functions import get_dialog_headers, get_project_headers, get_assistant_session
from voiceflow_functions import handle_response
from functions import transform_transcript_names

def post_launch_request(sessionID: str) -> dict:
  """
  Sends a launch request to initiate a session with a Voiceflow runtime environment.

  Parameters:
      sessionID (str): The session identifier for the Voiceflow runtime.

  Returns:
      dict: The response from the Voiceflow API after processing the launch request.

  Note:
      This function utilizes `get_dialog_headers` to retrieve the necessary headers for the request.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{sessionID}/interact?logs=off"
  payload = {
    "action": {
      "type": "launch"
    },
    "config": {
      "tts": False,
      "stripSSML": True,
      "stolAll": True,
      "excludeTypes": ["block", "debug", "flow"]
    }
  }
  dialog_headers = get_dialog_headers()
  response = requests.post(url, json=payload, headers=dialog_headers)
  return handle_response(response)

def fetch_state(user_id: str) -> dict:
  """
  Fetches the current state of a session from the Voiceflow API.

  Parameters:
      user_id (str): The user identifier for which the session state is retrieved.

  Returns:
      dict: The current state of the user's session as a JSON object.

  Note:
      Uses `get_dialog_headers` to obtain headers for the HTTP request.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}"
  dialog_headers = get_dialog_headers()
  response = requests.get(url, headers=dialog_headers)
  return response.json()

def delete_state(user_id: str) -> dict:
  """
  Deletes a user's session state in the Voiceflow runtime.

  Parameters:
      user_id (str): The user identifier whose session state is to be deleted.

  Returns:
      dict: The API response as a JSON object after deleting the state.

  Note:
      Calls `get_dialog_headers` to fetch headers needed for the HTTP request.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}"
  dialog_headers = get_dialog_headers()
  response = requests.delete(url, headers=dialog_headers)
  return response.json()

def post_text(user_id: str, text: str) -> dict:
  """
  Sends a text input to the Voiceflow API to simulate a user's text message in the session.

  Parameters:
      user_id (str): The user identifier for the Voiceflow session.
      text (str): The text input to be sent to the session.

  Returns:
      dict: The response from the Voiceflow API after processing the text input.

  Note:
      Utilizes `get_dialog_headers` to get the necessary headers and `handle_response` to process the API response.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/interact?logs=off"
  payload = {"action": {"type": "text", "payload": text}}
  dialog_headers = get_dialog_headers()
  response = requests.post(url, json=payload, headers=dialog_headers)
  return handle_response(response)


def post_button(user_id: str, button_id: str) -> dict:
  """
  Simulates a button press in a Voiceflow session by sending a button action type.

  Parameters:
      user_id (str): The user identifier for the Voiceflow session.
      button_id (str): The identifier of the button that is being "pressed".

  Returns:
      dict: The response from the Voiceflow API after processing the button press.

  Note:
      Calls `get_dialog_headers` for request headers and `handle_response` to manage the API response.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/interact?logs=off"
  payload = {"action": {"type": button_id, 'payload': {'label': ''}}}
  dialog_headers = get_dialog_headers()
  response = requests.post(url, json=payload, headers=dialog_headers)
  return handle_response(response)

def update_variable(user_id: str, key: str, value: str):
  """
  Updates a variable in the Voiceflow runtime for a specific user session.

  Parameters:
      user_id (str): The user identifier in the Voiceflow session.
      key (str): The name of the variable to update.
      value (str): The new value to set for the variable.

  Returns:
      str: Confirmation message indicating successful update of the variable.

  Note:
      Utilizes `get_dialog_headers` to obtain the necessary headers for the PATCH request.
  """
  url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/variables"
  payload = {key: value}
  dialog_headers = get_dialog_headers()
  requests.patch(url, json=payload, headers=dialog_headers)
  return "Variable succesfully updated"

def create_transcript(sessionID: str, projectID, device, oss,
  browser):
  """
  Creates a transcript record for a session in the Voiceflow database.

  Parameters:
      sessionID (str): The session identifier.
      projectID: The project identifier associated with the session.
      device: The type of device used in the session.
      os: The operating system used during the session.
      browser: The browser used during the session.

  Returns:
      dict: The response from the Voiceflow API as a JSON object after creating the transcript.

  Note:
      Calls `get_assistant_session` to retrieve session details, and `get_project_headers` for necessary request headers.
  """
  assistant_session = get_assistant_session()
  versionId = ''
  if assistant_session:
    versionId = assistant_session['version_id']
  url = "https://api.voiceflow.com/v2/transcripts"
  payload = {
  "versionID": versionId,
  "sessionID": sessionID,
  }
  optional_params = {
  "projectID": projectID,
  "device": device,
  "os": oss,
  "browser": browser
  }
  payload.update({k: v for k, v in optional_params.items() if v is not None})
  headers = get_project_headers()
  response = requests.put(url, json=payload, headers=headers)
  return response.json()

def retrieve_transcripts():
  """
  Retrieves transcripts from both the Voiceflow API and local database, and transforms their names for unified presentation.

  Returns:
      JSON or None: A JSON object containing the combined list of transcripts or an error message.

  Note:
      Uses `get_all_transcripts` to fetch transcripts from the local database and `transform_transcript_names` to standardize transcript names before returning them.
  """
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
    sql_transcripts = get_all_transcripts()
    transformed = transform_transcript_names(res.json(), sql_transcripts)
    
    return jsonify({
        'message': 'Retrieved transcripts.',
        'transcripts': transformed
    }), 200
  elif res.status_code == 401:
    return jsonify({'message': 'Invalid session.'}), 401
  else:
    print(f'Failed to retrieve transcripts. {res.status_code}')
    return jsonify({'message': 'Could not retrieve transcripts.'}), 400
