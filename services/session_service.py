from flask import Flask, jsonify, g, current_app, request
from config import user_session_serializer, assistant_session_serializer

# set session none => dashboard
def check_assistant_session(app: Flask, session):
  """
  Validates the given session string using the assistant session serializer. This function
  checks if the session data exists and whether it is valid according to the serialization scheme.

  Parameters:
      app (Flask): The Flask application instance, used for contextual application data.
      session (str): The session data string to be validated.

  Returns:
      bool or dict: Returns False if the session data is invalid or does not exist. If the session
                    is valid, returns the deserialized session data as a dictionary.

  Raises:
      Exception: Catches and logs exceptions related to invalid session data, typically from failed
                 deserialization, and returns False.

  Usage:
      result = check_assistant_session(current_app, session_str)
      if result:
          # Proceed with session-specific logic
      else:
          # Handle invalid or expired session
  """
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
  """
  Middleware function to validate user sessions for requests. It exempts certain endpoints from validation,
  checks for valid session tokens in request cookies, and loads the session if valid.

  Exemptions:
      This function does not check sessions for endpoints related to user authentication and initialization
      such as login, registration, logout, and specific OpenAI operations.

  Returns:
      None or JSON response: Directly returns None if the session is valid or if the endpoint is exempt.
                              Returns a JSON error response with a 401 status if the session is invalid.

  Raises:
      Exception: Handles exceptions from session deserialization and returns an appropriate JSON error.

  Usage:
      Should be used as a decorator or a before_request function in Flask to secure endpoints.
  """
  exempt_endpoints = ['users.login_route', 'users.register_route', 'users.logout_route',
                      'openai.initialize', 'openai.openai_chat', 'auth.google_login']
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