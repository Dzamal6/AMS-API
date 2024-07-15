from flask import Blueprint, request, jsonify, make_response, current_app
import requests
from services.openai_service import safely_end_chat_session
from util_functions.functions import check_module_permission, check_user_modules, decrypt_token, encrypt_token, get_agent_session, get_chat_session, get_module_session, roles_required, get_user_info, check_user_projects, check_admin
from services.sql_service import create_new_module, delete_module, get_all_modules, get_module_by_id, upload_agent_metadata
from config import FERNET_KEY, module_session_serializer

module_bp = Blueprint('module', __name__)

@module_bp.route('/set_module', methods=['POST'])
def set_module():
    """
  Sets up a session for a specified module if the user is authorized, 
  and stores relevant session data in a cookie.

  URL:
  - POST /set_module

  Parameters:
      module_id (str): The ID of the module for which the session is to be set up.

  Returns:
      JSON response (dict): A message indicating the success of the setup, along with module details
                            such as `Name`, `Id`, and `Created`, or an error message.

  Status Codes:
      200 OK: Project set successfully.
      400 Bad Request: Invalid request payload or an error occurred.
      401 Unauthorized: User is not allowed to access the specified module.
  """
    module_id = request.json.get('module_id')
    if not check_admin() and not check_module_permission(module_id):
        return jsonify({'error': 'User does not have access to this module.'}), 401
    
    module = get_module_by_id(module_id)
    
    if module is not None and isinstance(module, dict):
        serializer = module_session_serializer
        token = serializer.dumps({
            'Id': str(module['Id']),
            'Name': module['Name'],
            'Voice': module['Voice'],
            'Analytics': module['Analytics'],
            'Summaries': module['Summaries'],
            'Created': module['Created']
        })
        print('Module token set')
        
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        response = make_response(
            jsonify({'module': {'Name': module['Name'], 'Id': str(module['Id']), 'Created': module['Created']}, 'message': 'Module token set.'}), 200)
        response.set_cookie('module_session',
                            token,
                            httponly=True,
                            secure=True,
                            samesite='none',
                            max_age=1209600)
        return response
    else:
        return jsonify({'error':
                    "Failed to set assistant."}), 400
        
@module_bp.route('/modules', methods=['GET'])
def get_modules_route():
    """
    Retrieves a list of all the modules that the user has access to from the database.

    URL:
    - GET /modules

    Returns:
        JSON response (dict): A list of modules or an error message.

    Status Codes:
        200 OK: List of modules retrieved successfully.
        400 Bad Request: Modules could not be retrieved.
        401 Unauthorized: User is not authenticated.
        404 Not Found: No modules found.

    Notes:
        User authentication is verified using the `get_user_info` function.
        The function checks if the user is an admin using the `check_admin` function.
    """
    modules = get_all_modules()
    user_session = get_user_info()
    if check_admin():
        return jsonify({'modules': modules}), 200
    
    modules = check_user_modules(modules, user_session['Modules'])
    
    if modules:
        return jsonify({'message': 'Retrieved available modules.', 'modules': modules}), 200
    else:
        if len(modules) == 0:
            return jsonify({'message': "No modules found."}), 404
        else:
            return jsonify({'message': 'Failed obtain modules.'}), 400
        

@module_bp.route('/modules', methods=['POST'])
@roles_required('admin')
def create_module_route():
  """
  Creates a new module in the database. 
  Also creates a default agent 'Director' which is essential for conducting multi-agent conversations and is used to 
  direct the interactions. The director agent is meant to be programmed to switch between agents
  (depending on the flow_control parameter) either semantically or by order.
  
  URL:
  - POST /module
  
  Parameters:
    name (str): The name of the new module.
    description (str): The description of the new module.
    flow_control (str): If the module conversations should be directed by AI or the user. The field accepts 'AI' for setting the module to be directed by AI
    and 'User' to set the module to be directed by the user. This is used e.g. when the user gives tasks that the module's AIs complete or when the user is not
    supposed to direct the conversation (trainings, interviews where the AI is interviewing the user). If not set, 'User' is assumed by default.
    voice (bool): Whether the module conversations should be conducted via tts and stt or not. False by default.
    convo_analytics (bool): Whether the module will analyze each saved conversation using AI. False by default. If set to true, creates an agent-analytic.
    summaries (bool): Whether the module will create a short summary of each saved conversation using AI. False by default. If set to true, creates an agent-summarizer.

Returns: 
    JSON response (dict): A message indicating whether the assistant was added successfully,
    along with the assistant `Name`, `Id`, and `Created` properties, or an error message.
    
Status Codes:
    200 OK: Module created successfully.
    400 Bad Request: Invalid request payload or an error occurred. Includes an error if a module with the same name already exists
    401 Unauthorized: User is not allowed to create modules.

Access Control:
    Only admin users can create modules.
  """
  print(request.json.get('module'))
  data = request.json.get('module')
  name = data['Name']
  description = data['Description']
  flow_control = data['FlowControl']
  voice = data['Voice']
  convo_analytics = data['ConvoAnalytics']
  summaries = data['Summaries']
  
  if (type(name) is not str) or (description and type(description) is not str) or (flow_control and type(flow_control) is not str):
      return jsonify({'error': "Fields include wrong types."}), 400
  if (voice and type(voice) is not bool) or (convo_analytics and type(convo_analytics) is not bool) or (summaries and type(summaries) is not bool):
      return jsonify({'error': "Fields include wrong types."}), 400
  
  if not name:
      return jsonify({'error': 'Missing required parameters.'}), 400
  
  data, status_code = create_new_module(name=name,
                                description=description,
                                flow_control=flow_control,
                                voice=voice,
                                convo_analytics=convo_analytics,
                                summaries=summaries)  
  if status_code == 400:
    return jsonify({'error':
            "An error occurred while adding the assistant."}), 400
    
  if status_code == 409:
    return jsonify({'error': "A module with the same name already exists."}), 409
        
  return jsonify({
          'message': 'Module added to the database.',
          'module': data
      }), 200
  

@module_bp.route('/modules', methods=['DELETE'])
@roles_required('admin')
def delete_module_route():
  """
  Deletes a specified module and all its related data from the database.

  URL:
  - DELETE /modules

  Parameters:
      module_id (str): The unique identifier of the module to delete.

  Returns:
      JSON response (dict): A message indicating whether the module was deleted successfully.

  Status Codes:
      200 OK: Module deleted successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Requires the `Admin` role for deleting assistants.
  """
  module_id = request.json.get('module_id')
  delete = delete_module(module_id)
  if delete:
    return jsonify({'message': 'Module deleted from the database.'}), 200
  else:
    return jsonify({'message': 'Could not delete module.'}), 400

@module_bp.route('/modules/session', methods=['DELETE'])
def reset_module_session():
    """
    Resets the module session cookie along with the chat and agent session cookies. If those are active, deletes the agents and files stored in
    in the session from OpenAI servers.
    
    URL:
    - DELETE /modules/session
    
    Returns:
        JSON response (dict): A message indicating whether the sessions were reset successfully.
        
    Status Codes:
      200 OK: All sessions deleted successfully.
      400 Bad Request: All or some sessions failed to be reset.
    """
    module_session = get_module_session()
    chat_session = get_chat_session()
    agent_session = get_agent_session()
    if not module_session and not chat_session and not agent_session:
        return jsonify({'message': 'No sessions are active.'}), 200
    
    if chat_session:
        chat_response_data, chat_status_code = safely_end_chat_session()
        response = make_response(jsonify({'chat_session': chat_response_data}), chat_status_code)
    else:
        response = make_response(jsonify('Successfully reset agent, module and agent session cookies.'), 200)
    
    response.set_cookie('module_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',
                        )
    response.set_cookie('chat_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',
                        )
    response.set_cookie('agent_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',
                        )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response