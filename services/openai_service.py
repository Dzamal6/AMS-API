import logging
from flask import jsonify
from flask.helpers import make_response
import tiktoken
import openai
from openai import BadRequestError, NotFoundError
import os
import json
from packaging import version
from config import OPENAI_CLIENT as client, chat_session_serializer
import time
from functions import get_chat_session
from services.sql_service import get_agent_data

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

if current_version < required_version:
  raise ValueError(
      f"Error: OpenAI version {openai.__version__} is less than required version {required_version}. Please upgrade OpenAI to the latest version."
  )
else:
  print("OpenAI version is compatible")


def chat_ta(assistant_id, thread_id, user_input):
  """
  Sends a message to an OpenAI assistant and manages the conversation within a specific thread, counting the tokens used.

  Parameters:
      assistant_id (str): The unique identifier for the AI assistant.
      thread_id (str): The identifier for the conversation thread.
      user_input (str): The user's message to the AI assistant.

  Returns:
      dict: A dictionary with either a 'success' key containing the assistant's response or an 'error' key with an error message.

  Notes:
      - Uses `tiktoken` library to count tokens for both the user's input and the assistant's response.
      - Manages messages and interactions via `client.beta.threads.messages.create` and `client.beta.threads.runs.create`.
      - Handles timeouts, returning an error if response time exceeds 55 seconds.

  Examples:
      >>> response = chat_ta('asst_abc123', 'thread_abc123', 'Hello, assistant!')
      >>> print(response)
      {'success': "Assistant's response text here."}

      >>> response = chat_ta('asst_abc123', '', 'Hello, assistant!')
      >>> print(response)
      {'error': 'missing thread_id'}
  """
  # Token Counting Input
  encoding = tiktoken.get_encoding("cl100k_base")
  encoding = tiktoken.encoding_for_model("gpt-4")
  
  inp_tokens = len(encoding.encode(user_input))
  inp_cost_tok = (0.01 / 1000) * inp_tokens
  print(
      f"Number of tokens input: {inp_tokens}\nCost of tokens: {inp_cost_tok}")
  
  if not thread_id:
    print('Error: Missing thread_id')
    return {'error': 'missing thread_id'}
  
  print(f"Received message: '{user_input}' for thread ID: {thread_id}")
  
  client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)
  start_time = time.time()
  while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run.id)
  
    if run_status.status == "completed":
      break
  
    if time.time() - start_time > 55:
      print("Timeout reached")
      return {'error': 'timeout'}
  
  messages = client.beta.threads.messages.list(thread_id=thread_id)
  response = messages.data[0].content[0].text.value
  
  print(f"Assistant Response: {response}")
  
  # Token Counting Response
  out_tokens = len(encoding.encode(response))
  out_cost_tok = (0.03 / 1000) * out_tokens
  print(
      f"Number of tokens response: {out_tokens}\nCost of tokens: {out_cost_tok}"
  )
  
  # Token Updates
  # update_assistant_tokens(assistant_name, inp_tokens, inp_cost_tok, out_tokens,
  #                         out_cost_tok)
  
  return {'success': response}


def create_agent(agent_id):
  """
  Creates a new agent on the OpenAI server or retrieves details of an existing agent based on the provided ID.

  Parameters:
      agent_id (str): The unique identifier for the agent, used to store or retrieve the agent's data locally.

  Returns:
      [str, list] or None: The unique identifier of the created or retrieved agent, or None if creation failed.

  Raises:
      OSError: If necessary directories or files cannot be created.
      IOError: If there's an error in reading from or writing to the local JSON file.
      ApiError: If there's an issue with the OpenAI client during agent creation or file upload.

  Notes:
      - Uses `client.beta.assistants.create` to create an agent with properties like name and instructions.
      - Manages file uploads via `client.files.create` and stores agent details locally in `/tmp/agents/{agent_id}.json`.
      - Ensures the `/tmp/agents` directory exists for storing agent data.

  Example:
      >>> agent_id = create_agent('1234')
      >>> print(agent_id)
      'unique-agent-id'
  """

  agent_data = get_agent_data(agent_id)
  file_ids = []
  if not agent_data or agent_data is None:
    return None
  
  chat_session = get_chat_session()

  if chat_session is not None and chat_session.get('agent_id') == agent_data['Id']:
    oai_agent_id = str(chat_session['agent_id'])
    print("Loaded existing assistant ID")
  else:
    if len(agent_data['Documents_IO']) > 0:
      files = agent_data['Documents_IO']
      file_ids = []
      for file in files:
        file_object = (file['name'], file['bytes'])
        upload_file = client.files.create(file=file_object, purpose='assistants')
        file_ids.append(upload_file.id)

      try: 
        agent = client.beta.assistants.create(name=agent_data['Name'],
          instructions=agent_data['Instructions'],
          model=agent_data['Model'],
          tools=[{
            "type": "file_search"
          }],
          tool_resources={"file_search": {"vector_stores": [{"file_ids": file_ids}]}},
         )
      except BadRequestError as e:
        print(f"Error: {e}")
        return None
    else:
      agent = client.beta.assistants.create(name=agent_data['Name'],
                                              instructions=agent_data['Instructions'],
                                              model=agent_data['Model']
                                             )
    oai_agent_id = agent.id

  return oai_agent_id, file_ids

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
  
  if chat_session is None:
    return None
  
  if chat_session['agent_id'] is not agent_id:
    logging.error(f'Could not find existing agent {agent_id}')

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
    
    response = client.beta.assistants.delete(assistant_id=chat_session['agent_id'])

  if response.deleted:
    return response.id
  else:
    logging.error(f'Failed to delete agent with Id {agent_id}')
    return None