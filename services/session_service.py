from flask import Flask, jsonify, g, current_app, request
from config import user_session_serializer, assistant_session_serializer

# set session none => dashboard
def check_assistant_session(app: Flask, session):
  serializer = assistant_session_serializer
  if not session:
    print('No session data.')
    return False

  try:
    return serializer.loads(session)
  except:
    print('Invalid or expired session data.')
    return False

def check_session_validation():
  exempt_endpoints = ['users.login_route', 'users.register_route', 'users.logout_route', 'openai.initialize', 'openai.chat']
  if request.method == "OPTIONS":
    return
  if request.endpoint not in exempt_endpoints:
    serializer = user_session_serializer
    session = request.cookies.get('user_session')
    if not session:
      return jsonify({'error': 'No session data.'}), 401

    try:
      g.user_session_data = serializer.loads(session)
    except:
      print('Invalid or expired session data.')
      return jsonify({'error': 'Invalid or expired session data.'}), 401