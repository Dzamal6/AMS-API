import logging
from flask import Blueprint, request
from flask.helpers import make_response
from flask.json import jsonify

from util_functions.functions import get_agent_session, get_chat_session, is_valid_uuid
from config import agent_session_serializer, chat_session_serializer


utility_bp = Blueprint('utilities', __name__)

@utility_bp.route('/utility/chat_cookies', methods=['POST'])
def update_chat_session():
    """
    Updates the chat and agent cookies to the currently used agents and files. This is mainly
    intended for switching agents mid-conversation. 
    The agent_session cookie is overwritten with the new data and chat_session cookie is updated to include those details
    along with the previous chat session data.
    
    NOTE: An active chat and agent session has to be set for this function to work as intended. Make sure to call
    `init_chat` or `initialize` before updating cookies.
    
    URL:
    - POST /utility/chat_session
    
    Parameters:
        agent_data (dict[str, str | dict): The data of the switched-to agent to be updated in cookies.
        This should be `agent_id`, `oai_agent_id` and `file_ids`, the `agent_id` being the database stored ID of the agent
        and the `oai_agent_id` being the OpenAI id of an existing assistant. The `file_ids` array should consist of 
        OpenAI file ids tied to the currently used agent.
        
    Status Codes:
        200 OK: Cookies were set successfully.
        400 Bad Request: Failed to set cookies because they were either invalid or required fields were not provided.
        500 Internal Server Error: An unhandled exception occurred.
    """
    agent_data = request.json.get('agent_data')
    
    if not agent_data:
        logging.error(f'Failed to resolve agent data.')
        return jsonify({'error': 'Missing required fields.'}), 400
    
    if 'agent_id' not in agent_data or 'oai_agent_id' not in agent_data or 'file_ids' not in agent_data:
        logging.error(f'Error updating chat session cookies because required fields are missing in {agent_data}')
        return jsonify({'error': f'Missing required fields in {agent_data}'}), 400
    
    agent_id = agent_data['agent_id']
    oai_agent_id = agent_data['oai_agent_id']
    file_ids = agent_data['file_ids']
    
    if is_valid_uuid(oai_agent_id):
        logging.error(f'Received invalid OpenAI agent ID.')
        return jsonify({'error': f'Invalid oai_agent_id format.'}), 400
    if not is_valid_uuid(agent_id):
        logging.error(f'Received invalid agent UUID.')
        return jsonify({'error': f'Invalid agent_id format.'}), 400
    
    chat_session = get_chat_session()
    
    if not chat_session:
        logging.error(f'Failed to resolve chat session cookie while attempting to update it with pointer agent.')
        return jsonify({'error': 'Failed to resolve chat session cookie.'}), 400
    
    try:
        agent_session_data = {
            'agent_id': agent_id,
            'oai_agent_id': oai_agent_id,
            'file_ids': file_ids
        }
        
        agent_session_serialized = agent_session_serializer.dumps(agent_session_data)
        
        if isinstance(agent_session_serialized, bytes):
            agent_session_serialized = agent_session_serialized.decode('utf-8')
            
    except Exception as e:
        logging.error(f'Error updating agent session cookies because {e}')
        return jsonify({'error': f'Error updating agent session cookie. {e}'}), 400
    try:
        agent_ids = chat_session['agent_ids']
        chat_id = chat_session['chat_id']
        thread_id = chat_session['thread_id']
        
        if 'vector_store_id' in chat_session:
            vector_store_id = chat_session['vector_store_id']
                
        if 'file_ids' in chat_session and len(chat_session['file_ids']) > 0:
            chat_file_ids = chat_session['file_ids']
            file_ids = chat_file_ids + file_ids
        agent_ids.append(oai_agent_id)
        
        chat_session_data = {
            'agent_ids': agent_ids,
            'chat_id': chat_id,
            'thread_id': thread_id,
            'file_ids': file_ids,
            'vector_store_id': vector_store_id
        }
        
        chat_session_serialized = chat_session_serializer.dumps(chat_session_data)
        
        if isinstance(chat_session_serialized, bytes):
            chat_session_serialized = chat_session_serialized.decode('utf-8')
            
    except Exception as e:
        logging.error(f'Error updating chat session cookie because {e}')
        return jsonify({'error': f'Error updating chat session cookie. {e}'}), 400
    
    if chat_session_serialized and agent_session_serialized:
        response = make_response(jsonify({'message': 'Agent and chat cookies updated.'}), 200)
        response.set_cookie('chat_session',
                      chat_session_serialized,
                      httponly=True,
                      secure=True,
                      samesite='none',
                      max_age=604800)
        response.set_cookie('agent_session',
                      agent_session_serialized,
                      httponly=True,
                      secure=True,
                      samesite='none',
                      max_age=604800)
        return response
    else:
        return jsonify({'error': 'Failed to update agent or chat session cookies.'}), 400