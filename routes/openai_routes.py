import json
import logging
import time
from flask import Blueprint, jsonify, request, g, current_app, after_this_request
from flask.helpers import make_response, stream_with_context
from flask.wrappers import Response
from openai._exceptions import APIError
from config import OPENAI_CLIENT as client, chat_session_serializer, agent_session_serializer
from services.sql_service import get_analytic_agent, get_module_by_id, get_summarizer_agent, update_chat_session
from util_functions.functions import CustomResponse, TimeoutException, get_agent_session, get_chat_session, get_module_session
from services.openai_service import batch_delete_agents, batch_delete_files, chat_ta, chat_util_agent, create_agent, delete_agent, initialize_agent_chat, safely_end_chat_session
from openai import NotFoundError

from util_functions.oai_functions import check_switch_agent, convert_attachments, convert_content, convert_content 

openai_bp = Blueprint("openai", __name__)

@openai_bp.route('/openai/initialize', methods=['POST'])
def initialize():
  """
  Initializes an OpenAI assistant (agent) using the specified ID. This is intended for setting up agents
  for specific tasks using the OpenAI assistant API.

  URL:
  - POST /openai/initialize

  Parameters:
      agent_id (str): The ID of the agent to be initialized. This is the ID of the database-stored metadata of the agent, not the OpenAI ID.

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

  new_oai_agent_id, file_ids = create_agent(agent_id)

  if not new_oai_agent_id or new_oai_agent_id is None:
    return jsonify({'error': 'Agent not found'}), 404
  
  chat_serializer = chat_session_serializer
  agent_serializer = agent_session_serializer
  session_data = chat_serializer.dumps({'agent_id': new_oai_agent_id, 'thread_id': thread.id, 'file_ids': file_ids})
  if isinstance(session_data, bytes):
    session_data = session_data.decode('utf-8')
    
  response = make_response(jsonify({'message': 'Created new agent and set its cookie.', 'thread_id': thread.id, 'agent_id': new_oai_agent_id}), 200)
  response.set_cookie('chat_session',
                      session_data,
                      httponly=True,
                      secure=True,
                      samesite='none',
                      max_age=604800)

  return response


@openai_bp.route('/openai/init_chat', methods=['POST'])
def initialize_chat():
  """
  Initializes an OpenAI assistant (agent) using the provided ID, creates a new thread and immediately sends a message to the agent using the new thread. 
  This reduces request overhead as agents can be initialized by sending a message to them directly - useful for multi-agent conversations.
  The thread ID is saved to the database and can later be retrieved for reviewing or resuming the conversation.
  
  URL:
  - POST /openai/init_chat
  
  Parameters:
    agent_id (str): The ID of the agent to be initialized. This is the ID of the database-stored metadata of the agent, not the OpenAI ID.
    message (str): The user message to be sent to the initialized agent.
    thread_id (str): The thread the conversation is being held on. If no thread_id is provided, a new thread will be initialized. 
    
  Returns
      JSON response (dict): A message indicating successful initialization with a new thread ID and agent ID including the response from the agent,
                            or an error message if the agent is not found.
  Status Codes:
      200 OK: Agent initialized successfully.
      404 Not Found: Agent with the specified ID not found.
      400 Bad Request: Failed to initialize agent or there was an error fetching its response.
  """
  start = time.time()
  agent_id = request.json.get('agent_id')
  thread_id = request.json.get('thread_id')
  user_input = request.json.get('message')
  
  if not agent_id or not user_input:
    logging.error(f"Missing required parameters: agent_id={agent_id}, user_input={user_input}")
    return jsonify({'error': 'Missing required fields.'}), 400
  
  print(f'THREAD: {thread_id}')
  
  if not thread_id: 
    chat_session = get_chat_session()
    if chat_session and 'thread_id' in chat_session:
      thread_id = chat_session['thread_id']
    else:
      # handle timeout
      thread_id = client.beta.threads.create(timeout=10).id
      logging.info(f'Created a new thread: {thread_id}')
  else:
    logging.info(f'Using existing thread: {thread_id}')
    
  init = initialize_agent_chat(agent_id=agent_id, thread_id=thread_id, user_input=user_input)
  end = time.time()
  logging.info(f'Complete chat initialization took {end - start} seconds')
  return init


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
  try:
    delete = delete_agent(agent_id)
  except NotFoundError as e:
    logging.error(f'NOT FOUND: Failed delete agent. {e}')
    return jsonify({'error': 'Could not delete agent.'}), 404
  except Exception as e:
    logging.error(f'ERROR: Failed delete agent. {e}')
    return jsonify({'error': 'Could not delete agent.'}), 409

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

  Returns:
      JSON response (dict): The chat response from the OpenAI assistant or an error message. The response may include a `switch_agent` field which if populated,
      the current agent will switch to the one sent back. In the case of the director being set to 'AI' the next agent will be the one 
      to which the current one points to.

  Status Codes:
      200 OK: Chat response received successfully.
      400 Bad Request: Invalid request payload or an error occurred.
  """
  start = time.time()
  user_input = request.json.get('message')

  if not user_input:
    print(f"Missing required parameters: user_input={user_input}")
    return jsonify({'error': 'Missing required fields.'}), 400
  
  chat_session = get_chat_session()
  if chat_session is None or 'agent_ids' not in chat_session or 'thread_id' not in chat_session:
    return jsonify({'error': 'Error resolving chat cookie.'}), 400
  agent_session = get_agent_session()
  if agent_session is None or 'oai_agent_id' not in agent_session:
    return jsonify({'error': 'Failed to resolve agent cookie'}), 400
  
  logging.info(f'Current agent session: {agent_session}')
  logging.info(f'Current chat session: {chat_session}')
  
  @stream_with_context
  def stream_response():
    try:
      for content in chat_ta(assistant_id=agent_session['oai_agent_id'], thread_id=chat_session['thread_id'], user_input=user_input):
        if isinstance(content, str):
          yield content
        elif isinstance(content, dict):
          yield json.dumps(content)
    except TimeoutException as e:
      logging.error(f'Error obtaining response. Operation timed out. {e}')
      yield json.dumps({'error': 'Operation timed out.', 'status_code': 408})
    except APIError as e:
      logging.error(f'Error occurred while processing chat message: {e}')
      yield json.dumps({'error': f'An error occurred while communicating with the agent. {e}', 'status_code': 400})
    except Exception as e:
      logging.error(f'Error occurred while processing chat message: {e}')
      yield json.dumps({'error': f'An error occurred while communicating with the agent. {e}', 'status_code': 400})
    finally:
      end = time.time()
      logging.info(f'Interaction took {end - start} seconds')
        
  response = Response(stream_response(), content_type='text/plain', status=200)
  
  return response

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

@openai_bp.route('/openai/check_session', methods=['GET'])
def check_thread_session():
  """
  Obtains and deserializes the `chat_session` cookie to validate its existence. If it exists, returns its thread_id and current agent_id.
  If the cookie exists and contains partial data, the method 'cleans it up'.
  The method also checks for existing messages on that thread and returns them if present to restore the conversation in the session.
  
  URL:
  - GET /openai/check_session
  
  Returns:
    JSON response (dict): A response with the `chat_session` information, including previous thread messages or an error message indicating failure.
    
  Status Codes:
    200 OK: Chat session information retrieved or there is no session present but connection established.
    400 Bad Request: Either failed to establish a connection, there was an error fetching session information, or failed to fetch thread messages from OpenAI.
  """
  chat_session = get_chat_session()
  module_session = get_module_session()
  module_name = ''
  if module_session and 'Name' in module_session:
    module_name = module_session['Name']
  if chat_session is None:
    return jsonify({'success': 'Established connection but no chat session is present', 'module_name': module_name}), 200
  
  if chat_session and 'agent_ids' in chat_session and 'thread_id' in chat_session:
    agent_id = chat_session['agent_ids'][len(chat_session['agent_ids']) - 1]
    thread_id = chat_session['thread_id']
    try:
      thread_messages = client.beta.threads.messages.list(thread_id)
    except NotFoundError as e:
      logging.error(f'No thread found with id {thread_id}')
      res_data, status_code = safely_end_chat_session()
      if status_code != 200:
        res_data.update({'message': f'No thread found with id {thread_id}'})
        return jsonify(res_data), status_code
      response = make_response(jsonify({'error': f'No thread found with id {thread_id}'}), 404)
      response.set_cookie('chat_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',)
      response.set_cookie('agent_session',
                '',
                max_age=0,
                secure=True,
                httponly=True,
                samesite='none',
                )
      return response
    except Exception as e:
      logging.error(f'Failed to fetch thread messages for thread {thread_id}')
      # res_data, status_code = safely_end_chat_session()
      # if status_code != 200:
      #   res_data.update({'message': f'Failed to fetch thread messages: {e}'})
      #   return jsonify(res_data), status_code
      response = make_response(jsonify({'error': f'Failed to fetch thread messages: {e}'}), 400)
      # response.set_cookie('chat_session',
      #                   '',
      #                   max_age=0,
      #                   secure=True,
      #                   httponly=True,
      #                   samesite='none',)
      # response.set_cookie('agent_session',
      #           '',
      #           max_age=0,
      #           secure=True,
      #           httponly=True,
      #           samesite='none',
      #           )
      return response

    if thread_messages:
        messages_list = []
        for msg in thread_messages:
          # print(f'message: {msg}')
          message_dict = {
              'Id': msg.id,
              'Created': msg.created_at,
              'Role': msg.role,
              'Content': convert_content(msg.content),
              'Attachments': convert_attachments(msg.attachments)
          }
          messages_list.append(message_dict)
          
        messages_list.reverse()

        return jsonify({
            'message': "Established connection and found an existing chat_session and retrieved its data.",
            'module_name': module_name,
            'agent_id': agent_id,
            'thread_id': thread_id,
            'messages': messages_list
        }), 200
    else:
      return jsonify({'message': "Established connection and found an existing chat_session but failed to retrieve thread messages", 'agent_id': agent_id, 'thread_id': thread_id, 'module_name': module_name}), 200
  elif chat_session and 'agent_ids' in chat_session:
    for agent in chat_session['agent_ids']:
      delete_agent(agent_id=agent)
    response = make_response(jsonify({'error': 'Chat session is present but missing required data. Cleaning up...', 'module_name': module_name}), 400)
    response.set_cookie('chat_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',)
    return response
  elif chat_session:
    response = make_response(jsonify({'error': 'Chat_session is present but missing required data. Cleaning up...', 'module_name': module_name}), 400)
    response.set_cookie('chat_session',
                        '',
                        max_age=0,
                        secure=True,
                        httponly=True,
                        samesite='none',)
    return response
  else:
    return jsonify({'error': 'Failed to establish connection.', 'module_name': module_name}), 400
  
@openai_bp.route('/openai/end_chat', methods=['DELETE'])
def end_session_chat():
  """
  Ends the chat session and deletes the chat session cookie. Also deletes all agents and files from OpenAI servers present in the cookie.
  
  URL:
  - DELETE /openai/end_chat
  
  Returns:
    JSON response (str | [str, list]): Json response with a status message or a list of undeleted agents or files.
  """
  response_data, status_code = safely_end_chat_session()
  
  response = make_response(jsonify(response_data), status_code)
  if status_code != 200:
    return response
  
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

@openai_bp.route('/openai/create_analytics', methods=['GET'])
def create_analytics_route():
  """
  Calls the module's 'Analyic' agent and generates analytics data using its `initial_prompt`.
  
  Parameters:
    module_id (str): The ID of the module the chatsession belongs to.
    thread_id (str): The ID of the thread the conversation was held on.
    
  Returns:
    JSON response: A Flask response object containing the analytics data and a status message.
  """
  module_id = request.args.get('module_id')
  thread_id = request.args.get('thread_id')
  chat_session_id = request.args.get('chat_session_id')
  
  if not module_id or not thread_id:
    return jsonify({'error': 'Missing required fields.'}), 400

  try:
    analytic_agent = get_analytic_agent(module_id)
    response = chat_util_agent(agent_id=analytic_agent['Id'],
                              thread_id=thread_id,
                              input=analytic_agent['InitialPrompt'],
                              chat_session_id=chat_session_id,
                              config='analysis')
    return response
    
  except Exception as e:
    logging.error(f'Failed to create analytics for thread {thread_id}. {e}')
    return jsonify({'error': f'Failed to create analytics for thread {thread_id}.'}), 500

@openai_bp.route('/openai/create_summary', methods=['GET'])
def create_summary_route():
  """
  Calls the module's 'Summarizer' agent and generates a summary using its `initial_prompt`.
  
  Parameters:
    module_id (str): The ID of the module the chatsession belongs to.
    thread_id (str): The ID of the thread the conversation was held on.
    
  Returns:
    JSON response: A Flask response object containing the summary and a status message.
  """
  module_id = request.args.get('module_id')
  thread_id = request.args.get('thread_id')
  chat_session_id = request.args.get('chat_session_id')
  
  if not module_id or not thread_id:
    return jsonify({'error': 'Missing required fields.'}), 400
  if module_id == 'None' or thread_id == 'None':
    return jsonify({'error': 'Cannot create summary!'}), 400
  
  try:
    summary_agent = get_summarizer_agent(module_id)
    response = chat_util_agent(agent_id=summary_agent['Id'],
                              thread_id=thread_id,
                              input=summary_agent['InitialPrompt'],
                              chat_session_id=chat_session_id,
                              config='summary')
    return response
  
  except Exception as e:
    logging.error(f'Failed to create summary for thread {thread_id}. {e}')
    return jsonify({'error': f'Failed to create summary for thread {thread_id}.'}), 500
