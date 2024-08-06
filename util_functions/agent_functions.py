import logging
import time

from flask import request, g, current_app
from openai._exceptions import BadRequestError
from services.sql_service import get_agent_data
from config import OPENAI_CLIENT as client, chat_session_serializer, agent_session_serializer
from services.storage_service import serve_file
from util_functions.functions import get_agent_session, get_chat_session, get_module_session


def switch_agent(agent_session):
    """
    Switches the current agent to a new one based on the agent pointer stored in the database.
    Updates the agent session and chat session cookies with the new agent data.
    
    Parameters:
        agent_session (dict): The currently set agent cookie.
    
    Returns:
        str or dict: The ID of the created OpenAI agent if successful, None otherwise.
    """
    start = time.time()
    try:
      if not agent_session:
        logging.warning(f'Agent attempted to switch agents before a cookie was set.')
        return 'Cannot switch agents yet!'
      agent_id = agent_session['agent_id']
      
      get_agent = get_agent_data(agent_id)
      if not get_agent or 'AgentPointer' not in get_agent:
          logging.error(f'Could not find `AgentPointer` field in {get_agent}')
          return 'Failed to switch agents! There is no other agent connected.'
      if get_agent['AgentPointer'] == 'None':
        logging.error(f'`AgentPointer` field in {get_agent} is set to None')
        return 'Failed to switch agents! There is no other agent connected.'
      
      get_agent_pointer = get_agent_data(get_agent['AgentPointer'])
      new_oai_agent_id, file_ids, vs_id = create_agent(get_agent_pointer['Id'])
      agent_session_data = {
          'agent_id': str(get_agent_pointer['Id']),
          'oai_agent_id': new_oai_agent_id,
          'file_ids': file_ids,
          'vector_store_id': vs_id
      }
    except Exception as e:
        logging.error(f'Failed to switch agents!: {e}')
        return 'Failed to switch agents!'
        
    end = time.time()
    logging.info(f'Switching agents took {end - start} seconds')
    return get_agent_pointer['InitialPrompt'], {'agent_session': agent_session_data}

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
  start = time.time()
  agent_data = get_agent_data(agent_id)
  file_ids = []
  if not agent_data or agent_data is None:
    return None
  
  agent_session = get_agent_session()
  chat_session = get_chat_session()
  module_session = get_module_session()
  tools = []
  tool_resources = {}
  vector_store_id = ''

  if agent_session is not None and agent_session.get('agent_id') == agent_data['Id']:
    oai_agent_id = str(agent_session['oai_agent_id'])
    print("Loaded existing assistant ID")
  # Check for existing agent in OpenAI (Introduce existing_agent_id to agent table?)
  else:
    if len(agent_data['Documents']) > 0:
      files = agent_data['Documents']
      
      file_ids = []
      
      for file in files:
        file_bytes = serve_file(file['URL'])
        if not file_bytes:
          return None
        file_object = (file['Name'], file_bytes)
        upload_file = client.files.create(file=file_object, purpose='assistants')
        file_ids.append(upload_file.id)
        
      if chat_session and 'vector_store_id' in chat_session:
        vector_store_id = chat_session['vector_store_id']
        try:
          client.beta.vector_stores.file_batches.create(vector_store_id=vector_store_id, file_ids=file_ids)
        except Exception as e:
          logging.error(f"Error updating vector store {vector_store_id}: {e}")
      else:
        try:
          vector_store = client.beta.vector_stores.create(name=f'temp_vs-{module_session['Name']}', file_ids=file_ids)
          vector_store_id = vector_store.id
        except Exception as e:
          logging.error(f"Error creating vector store: {e}")
      tools.append({"type": "file_search"})
      tool_resources = {"file_search": {"vector_store_ids": [vector_store_id]}}

      # try: 
      #   agent = client.beta.assistants.create(name=agent_data['Name'],
      #     instructions=agent_data['Instructions'],
      #     model=agent_data['Model'],
      #     tools=[{
      #       "type": "file_search"
      #     }],
      #     tool_resources={"file_search": {"vector_stores": [{"file_ids": file_ids}]}},
      #    )
      # except BadRequestError as e:
      #   print(f"Error: {e}")
      #   return None
    # else:
    # agent = client.beta.assistants.create(name=agent_data['Name'],
    #                                       instructions=agent_data['Instructions'],
    #                                       model=agent_data['Model']
    #                                      )
    if 'AgentPointer' in agent_data and agent_data['AgentPointer'] is not None and agent_data['AgentPointer'] != 'None':
      # agent = client.beta.assistants.update(assistant_id=agent.id, tools=[{
      #   'type': 'function',
      #   'function': {
      #     'name': 'point_to_agent',
      #     'description': 'Function for switching to another agent.'
      #   }
      #   }])
      tools.append({
        'type': 'function',
        'function': {
          'name': 'point_to_agent',
          'description': 'Function for switching to another agent.'
        }})
      
    try:
      if tools and tool_resources:
        agent = client.beta.assistants.create(name=agent_data['Name'],
                                            instructions=agent_data['Instructions'], 
                                            model=agent_data['Model'], 
                                            tools=tools,
                                            tool_resources=tool_resources)
      else:
        agent = client.beta.assistants.create(name=agent_data['Name'],
                                              instructions=agent_data['Instructions'],
                                              model=agent_data['Model']
                                            )
    except Exception as e:
      logging.error(f'Error creating agent {agent_id} in OpenAI. {e}')
      return None
    
    oai_agent_id = agent.id
  end = time.time()
  logging.info(f'Agent creation took {end - start} seconds')
  return oai_agent_id, file_ids, vector_store_id