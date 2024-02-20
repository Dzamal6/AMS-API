from flask import Blueprint, request, jsonify
from functions import get_user_info, get_assistant_session
import services.voiceflow_service as vs

voiceflow_bp = Blueprint('voiceflow', __name__)

@voiceflow_bp.route("/voiceflow/launch", methods=["POST"])
def launch():
  user = get_user_info()
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.post_launch_request(user['Id'])), 200

@voiceflow_bp.route("/voiceflow/fetch_state", methods=["POST"])
def fetch():
  user = get_user_info()
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.fetch_state(user['Id'])), 200

@voiceflow_bp.route("/voiceflow/delete_state", methods=["DELETE"])
def delete():
  user = get_user_info()
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.delete_state(user)), 200

@voiceflow_bp.route('/voiceflow/interact', methods=["POST"])
def interact():
  user = get_user_info()
  response = request.json.get("text", None)
  btn = request.json.get("btn", None)

  if not user:
    return jsonify({"message": "Unauthorized"}), 401

  if btn is None and response is None:
    return jsonify({"error": "No sufficient response was provided."}), 400

  print(f'btn: {btn}; response: {response}')
  if btn:
    return jsonify(vs.post_button(user['Id'], btn)), 200
  else:
    return jsonify(vs.post_text(user['Id'], response)), 200

@voiceflow_bp.route("/voiceflow/update_variable", methods=["PATCH"])
def update_variable():
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
  user = get_user_info()
  assistant_session = get_assistant_session()
  device = request.json.get('device', None)
  oss = request.json.get('os', None)
  browser = request.json.get('browser', None)

  if not assistant_session:
    return jsonify({'error': "No assistant session"}), 400
  
  if not user:
    return jsonify({"error": "You need a user"}), 400

  create = vs.create_transcript(user['Id'], assistant_session['project_id'], device, oss, browser)

  print(f"Create: {create}")

  if create.get('message') and create['message'] == 'Unauthorized':
    return jsonify({'error': create}), 400
    
  return create, 200