import json
import logging
import time
from flask import jsonify
from flask.helpers import make_response, stream_with_context
from flask.wrappers import Response
from openai._exceptions import APIError
from openai.types.beta.assistant_stream_event import ThreadMessageDelta, ThreadRunRequiresAction, ThreadRunStepDelta
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
import openai
from openai import BadRequestError, NotFoundError
from packaging import version
from config import OPENAI_CLIENT as client, chat_session_serializer, agent_session_serializer
from time import sleep
from util_functions.agent_functions import create_agent, switch_agent
from util_functions.functions import TimeoutException, get_agent_session, get_chat_session, get_module_session, get_user_info, timeout
from services.sql_service import db_create_chat_session, get_agent_data, update_chat_session
from util_functions.oai_functions import include_init_message, safely_delete_last_messages, wrap_message

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

if current_version < required_version:
  raise ValueError(
      f"Error: OpenAI version {openai.__version__} is less than required version {required_version}. Please upgrade OpenAI to the latest version."
  )
else:
  print("OpenAI version is compatible")

@timeout(4)
def chat_ta(assistant_id:str, thread_id:str, user_input:str, initial:bool=False, agent_id:str=None):
  """
  Sends a message to an OpenAI assistant and manages the conversation within a specific thread, counting the tokens used.
  This method also wraps the user message with wrapper prompts according to its parameters and the agent's data.

  Parameters:
      assistant_id (str): The unique identifier for the OpenAI assistant.
      thread_id (str): The identifier for the conversation thread.
      user_input (str): The user's message to the AI assistant.
      initial (bool): If the user_input comes from an initial interaction. Defaults to False. This is meant for initializing new agents amidst a conversation, it is not needed at the beginning.
      agent_id (str): If `initial` is set to True, an `agent_id` is required to find the initial wrapper prompt.

  Returns:
      dict: A dictionary with either a 'success' key containing the assistant's response or an 'error' key with an error message.

  Notes:
      - Uses `tiktoken` library to count tokens for both the user's input and the assistant's response.
      - Manages messages and interactions via `client.beta.threads.messages.create` and `client.beta.threads.runs.create`.
      - Handles timeouts, returning an error if response time exceeds 55 seconds.
      - If `initial` is set to True, deletes last two messages (prompt + response). This is a cleanup method, since the response
      containing the switch flag doesn't need to be displayed.

  Examples:
      >>> response = chat_ta('asst_abc123', 'thread_abc123', 'Hello, assistant!')
      >>> print(response)
      {'success': "Assistant's response text here."}

      >>> response = chat_ta('asst_abc123', '', 'Hello, assistant!')
      >>> print(response)
      {'error': 'missing thread_id'}
  """
  # time.sleep(10)
  
  if not thread_id:
    print('Error: Missing thread_id')
    return {'error': 'missing thread_id'}
  
  print(f"Received message: '{user_input}' for thread ID: {thread_id}")
  
  wrapper = user_input
  agent_session = get_agent_session()
  if initial:
    if not agent_id:
      raise NotFoundError(f'Missing agent_id!')
    else:
      safely_delete_last_messages(thread_id=thread_id) # This placement removes context of the deleted messages for the upcoming response, but risks deleted messages even if the conversation fails.
      agent_data = get_agent_data(agentId=agent_id)
    
      initial_present, initial_input = include_init_message(user_input, agent_data=agent_data, config='concat')
      if not initial_present:
        initial_input = wrap_message(user_input, agent_data=agent_data, config='start')
      wrapper = initial_input
      logging.info(f'Wrapping message: {wrapper}')
  else:
    if not agent_session or 'agent_id' not in agent_session:
      logging.warning(f'Could not resolve agent_session cookie. Failed to alter message...')
    else:
      agent_data = get_agent_data(agentId=agent_session['agent_id']) # put this into cookies so it doesn't slow down the chat
      wrapper = wrap_message(wrapper, agent_data=agent_data, config='start')
      logging.info(f'Wrapping message: {wrapper}')
  
  client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=wrapper)
  
  stream = client.beta.threads.runs.create(thread_id=thread_id, timeout=55,
                                        assistant_id=assistant_id, stream=True, additional_instructions='Do not use the function unless the user tells you to. Also do not create any additional functions.')
  for event in stream:  
    # print(event)
    if isinstance(event, ThreadMessageDelta):
      if isinstance(event.data.delta.content[0], TextDeltaBlock):
        yield event.data.delta.content[0].text.value
      sleep(0.05)
    if isinstance(event, ThreadRunStepDelta):
      if event.data.delta.step_details.tool_calls[0].function is not None and event.data.delta.step_details.tool_calls[0].function.name is not None:
        yield json.dumps({'action': 'function_call', 'function_name': event.data.delta.step_details.tool_calls[0].function.name, 'status': 'in_progress'})
        sleep(0.5)
          
    if isinstance(event, ThreadRunRequiresAction):
      tool_calls = event.data.required_action.submit_tool_outputs.tool_calls
      tool_outputs = []
      for tool_call in tool_calls:
        print(f'Calling {tool_call.function.name}')
        if tool_call.function.name == 'point_to_agent':
          result = switch_agent(agent_session=agent_session)
          if isinstance(result, tuple):
            result, cookies = result  
            print(f'output: {result if result else 'Cannot switch agents!'}')
            print(f'output cookies: {cookies}')
            tool_outputs.append({'tool_call_id': tool_call.id, 'output': result})
            if cookies:
              yield json.dumps({'action': 'function_call', 'function_name': tool_call.function.name, 'status': 'completed'})
              sleep(0.5)
              yield cookies
          else:
            tool_outputs.append({'tool_call_id': tool_call.id, 'output': result})
            yield json.dumps({'action': 'function_call', 'function_name': tool_call.function.name, 'status': 'failed'})
        else:
          tool_outputs.append({'tool_call_id': tool_call.id, 'output': 'Function does not exist.'})
      with client.beta.threads.runs.submit_tool_outputs_stream(thread_id=thread_id, run_id=event.data.id, tool_outputs=tool_outputs) as stream_output:
        for text in stream_output.text_deltas:
          yield text
          sleep(0.05)

def delete_agent(agent_id: str):
  """
  Deletes an agent from the OpenAI server and its associated local file based on the provided agent ID.

  Parameters:
      agent_id (str): A unique identifier for the agent to be deleted.

  Returns:
      str or None: The unique identifier of the deleted agent or None if the deletion failed.

  Raises:
      OSError: If unable to delete the local file.
      ApiError: If the OpenAI client fails to delete the agent.

  Notes:
      - Utilizes the `client.beta.assistants.delete` API call to delete the agent from the server.
      - Checks for the agent's existence by looking for a corresponding local file.
  """
  chat_session = get_chat_session()
  
  # if chat_session is None:
  #   return None
  
  # if chat_session['agent_id'] is not agent_id:
  #   logging.error(f'Could not find existing agent {agent_id}')

  if chat_session['file_ids'] is not []:
    for file_id in chat_session['file_ids']:
      try:
        client.files.delete(file_id)
      except NotFoundError as nf:
        print(f'Failed to delete file: {nf}')
        continue
      except BadRequestError as e:
        print(f'Failed to delete file: {e}')
        continue
      print(f'Removed file: {file_id} from OpenAI.')
    
  response = client.beta.assistants.delete(assistant_id=agent_id)

  if response.deleted:
    return response.id
  else:
    logging.error(f'Failed to delete agent with Id {agent_id}')
    return None
  
def initialize_agent_chat(agent_id: str, thread_id: str, user_input: str):
  """
  Initializes a new OpenAI agent and immediately sends a message to that agent. 
  The method sets a cookie for the chat session if none exists, and adds agent_ids and file_ids used within the `chat_session` to the cookie if it already exists. 
  This is very useful for later deleting the used files and agents from OpenAI.
  An `agent_session` cookie is also set to track the current agent used and its files.
  A ChatSession is added to the database with the thread_id if no `chat_session` cookie is present.
  
  Parameters:
    agent_id (str): The ID of the agent to be initialized. This is the ID of the database-stored metadata of the agent, not the OpenAI ID.
    thread_id (str): The ID of the thread the conversation is currently being held on.
    user_input (str): The user message to be sent to the initialized agent.
    
  Returns
    JSON response (dict): A message indicating successful initialization with a new thread ID and OAI agent ID including the response from the agent,
                          or an error message if the agent is not found.
  """
  new_oai_agent_id, file_ids = create_agent(agent_id)

  if not new_oai_agent_id or new_oai_agent_id is None:
    return jsonify({'error': 'Agent not found'}), 404
  
  agent_serializer = agent_session_serializer
  # IMPORTANT: agent_id: Database-stored agent, oai_agent_id: OpenAI ID of the temp agent, file_ids: OpenAI IDs of temporarily stored files on OpenAI.
  agent_data = agent_serializer.dumps({'agent_id': agent_id, 'oai_agent_id': new_oai_agent_id, 'file_ids': file_ids})
  if isinstance(agent_data, bytes):
    agent_data = agent_data.decode('utf-8')
  
  chat_session = get_chat_session()
  
  chat_id = None
  if not chat_session or 'chat_id' not in chat_session:
    module_session = get_module_session()
    if not module_session:
      return jsonify({'error': 'Module session not found'}), 404
    user_session = get_user_info()
    if not user_session or 'Id' not in user_session:
      return jsonify({'error': 'Invalid user session or user session could not be resolved'}), 400
    db_chat = db_create_chat_session(thread_id, module_session['Id'], user_id=user_session['Id'])
    chat_id = db_chat['Id']
  else:
    chat_id = chat_session['chat_id']
  
  agent_ids = []
  if chat_session and 'agent_ids' in chat_session and 'file_ids' in chat_session:
    agent_ids = chat_session['agent_ids']
    file_ids.append(chat_session['file_ids'])
    
  agent_ids.append(new_oai_agent_id)
  
  chat_serializer = chat_session_serializer
  
  session_data = chat_serializer.dumps({'agent_ids': agent_ids, 'thread_id': thread_id, 'file_ids': file_ids, 'chat_id': chat_id})
  logging.info(f"CURRENT CHAT SESSION DATA: 'agent_ids': {agent_ids}, 'thread_id': {thread_id}, 'file_ids': {file_ids}")
  if isinstance(session_data, bytes):
    session_data = session_data.decode('utf-8')
  
  @stream_with_context
  def stream_response():
    try:
      for content in chat_ta(assistant_id=new_oai_agent_id, thread_id=thread_id, user_input=user_input, initial=True, agent_id=agent_id):
        yield content
    except TimeoutException as e:
      logging.error(f'Error obtaining response. Operation timed out. {e}')
      yield json.dumps({'error': 'Operation timed out.', 'status_code': 408})
    except APIError as e:
      logging.error(f'Error occurred while processing chat message: {e}')
      yield json.dumps({'error': f'An error occurred while communicating with the agent. {e}', 'status_code': 400})
    except Exception as e:
      logging.error(f'Error occurred while processing chat message: {e}')
      yield json.dumps({'error': f'An error occurred while communicating with the agent. {e}', 'status_code': 400})
  
  response = Response(stream_response(), content_type='text/plain', status=200)
  response.set_cookie('chat_session',
                      session_data,
                      httponly=True,
                      secure=True,
                      samesite='none',
                      max_age=604800)
  response.set_cookie('agent_session',
                      agent_data,
                      httponly=True,
                      secure=True,
                      samesite='none',
                      max_age=604800)

  return response


def batch_delete_agents(agent_ids: list[str]):
  """
  Deletes agents from OpenAI servers.
  
  Returns:
    True or False, list: True if agents are deleted successfully and False if the deletion process fails. If False is returned, so is the list of non-deleted agents.
  """
  failed_agents = []
  if not agent_ids:
    return True, failed_agents
  
  logging.info(f'Attempting to delete agents from OpenAI [{[agent_id for agent_id in agent_ids]}]')
  
  valid_agent_ids = [agent_id for agent_id in agent_ids if agent_id]
  
  print(f'VALID AGENT IDS: {valid_agent_ids}')
  
  for agent_id in valid_agent_ids:
    try:
      delete = client.beta.assistants.delete(agent_id)
      if not delete.deleted:
        logging.info(msg=f'Failed to delete agent [{agent_id}]')
        failed_agents.append(agent_id)
      else:
        logging.info(msg=f'Successfully deleted agent [{agent_id}]')
    except NotFoundError as e:
      logging.error(f'Agent {agent_id} not found. {e}')
      continue
    except ValueError as e:
      logging.error(f'Invalid agent_id {agent_id}. {e}')
      continue
    
  if not failed_agents:
    return True, failed_agents
  else:
    return False, failed_agents
    
def batch_delete_files(file_ids: list[str]):
  """
  Deletes files from OpenAI servers.
  
  Returns:
    True or False and list: True if the deletion is fully successfull and False when it fails. A list of non-deleted files_ids is returned on fail.
  """
  failed_files = []
  if not file_ids:
    return True, failed_files
  
  logging.info(f'Attempting to delete files from OpenAI [{[file for file in file_ids]}]')
  
  valid_file_ids = [file_id for file_id in file_ids if file_id]

  for file_id in valid_file_ids:
    try:
      delete = client.files.delete(file_id)
      if not delete.deleted:
        logging.error(f'Failed to delete file [{file_id}]')
        failed_files.append(file_id)
      else:
        logging.info(f'Deleted file {file_id}')
    except NotFoundError as e:
      logging.error(f'File {file_id} not found. {e}')
    except ValueError as e:
      logging.error(f'Invalid file_id {file_id}. {e}')
      failed_files.append(file_id)
  
  if not failed_files:
    return True, failed_files
  else:
    return False, failed_files
  
def safely_end_chat_session():
  """
  Attempts to iteratively remove agents and files used during the chat session from OpenAI servers.
  The method retrieves the chat_session cookie and uses the agent_ids and file_ids to identify files for removal.
  The ChatSession in the database is updated to contain the last agent used by the chat session.
  A summary and analytics are created if set in the module settings.
  
  Returns:
    dict[str, str | list], literal[200 | 400]: A message along with data and a status code indicating the success or failure of the method.
  """
  chat_session = get_chat_session()
  
  if not chat_session or chat_session is None or 'agent_ids' not in chat_session:
      return {'error': 'Could not resolve chat session cookie.'}, 400
  
  file_ids = []
  agent_ids = chat_session['agent_ids']
  if 'file_ids' in chat_session:
      file_ids = chat_session['file_ids']
  
  agents_status, agents_deleted = batch_delete_agents(agent_ids)
  files_status, files_deleted = batch_delete_files(file_ids)
  
  if not agents_status and not files_status:
      logging.error(f'Failed to delete files: {files_deleted} and agents {agents_deleted}')
      return {'error': 'Failed to delete all or some agents and files.', 'non_deleted_files': files_deleted, 'non_deleted_agents': agents_deleted}, 400
  
  if not files_status:
      logging.error(f'Failed to delete files: {files_deleted}')
      return {'error': "Failed to delete all or some files", 'non_deleted_files': files_deleted}, 400
  
  if not agents_status:
      logging.error(f'Failed to delete agents: {agents_deleted}')
      return {'error': "Failed to delete all or some agents", 'non_deleted_agents': agents_deleted}, 400
  
  return {'message': 'Agents and files removed from OpenAI.'}, 200

def chat_util_agent(agent_id: str, thread_id: str, input: str, chat_session_id: str, config: str):
  """
  Initializes, messages and then deletes a utility agent. Intended for utility operations like conducting analysis or
  summaries at the end of a conversation.
  
  Parameters:
    agent_id (str): The ID of the database-stored agent to be used.
    thread_id (str): The ID of the thread the chat is being held on.
    input (str): The input to be sent to the agent. This should be a thoroughly curated prompt so that the agent carries the operation out correctly and consistently.
    chat_session_id (str): The ID of the chat session the response will belong to.
    config (str): Either 'analysis' or 'summary'. Used for determining whether to store the response as an analysis or a summary.
    
  Returns:
    dict: A dictionary with either a 'success' key containing the assistant's response or an 'error' key with an error message.
  """
  oai_agent_id, file_ids = create_agent(agent_id=agent_id)
  
  @stream_with_context
  def stream_response():
    full_response = ''
    try:
      for content in chat_ta(assistant_id=oai_agent_id, thread_id=thread_id, user_input=input):
        full_response += content
        yield content
    finally:
      safely_delete_last_messages(thread_id=thread_id)
      client.beta.assistants.delete(assistant_id=oai_agent_id)
      messages = client.beta.threads.messages.list(thread_id=thread_id)
      if config == 'analysis':
        update_chat_session(chat_session_id=chat_session_id, analysis=full_response, messages_len=len(messages.data))
      elif config == 'summary':
        update_chat_session(chat_session_id=chat_session_id, summary=full_response, messages_len=len(messages.data))

  response = Response(stream_response(), content_type='text/plain', status=200)
  
  return response