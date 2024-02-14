from flask import Blueprint, request, jsonify

import services.voiceflow_service as vs

voiceflow_bp = Blueprint('voiceflow', __name__)

@voiceflow_bp.route("/voiceflow/launch", methods=["POST"])
def launch():
  user = request.json.get("user", None)
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.post_launch_request(user)), 200

@voiceflow_bp.route("/voiceflow/fetch_state", methods=["POST"])
def fetch():
  user = request.json.get("user", None)
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.fetch_state(user)), 200

@voiceflow_bp.route("/voiceflow/delete_state", methods=["DELETE"])
def delete():
  user = request.json.get("user", None)
  if not user:
    return jsonify({"error": "You need a user"}), 400
  return jsonify(vs.delete_state(user)), 200

@voiceflow_bp.route('/voiceflow/interact', methods=["POST"])
def interact():
  user = request.json.get("user", None)
  response = request.json.get("text", None)
  btn = request.json.get("btn", None)

  if not user and not response:
    return jsonify({"error": "You need a user and a text"}), 400

  if btn:
    return jsonify(vs.post_button(user, response)), 200
  else:
    return jsonify(vs.post_text(user, response)), 200

@voiceflow_bp.route("/voiceflow/update_variable", methods=["PATCH"])
def update_variable():
  user = request.args.get('user')
  if user:
    return jsonify({"message": vs.update_variable(user, request.json)}), 200
  else:
    return jsonify({"error": "user is needed"}), 400

@voiceflow_bp.route("/voiceflow/create-transcript", methods=["PUT"])
def transcript():
  session_id = request.json.get('user', None)
  project_id = request.json.get('projectID', None)
  device = request.json.get('device', None)
  oss = request.json.get('os', None)
  browser = request.json.get('browser', None)

  if not user:
    return jsonify({"error": "You need a user"}), 400

  return jsonify(vs.create_transcript(session_id, project_id, device, oss, browser))