from flask.blueprints import Blueprint
from flask.json import jsonify
from flask import request
from config import OPENAI_CLIENT as client, chat_session_serializer, agent_session_serializer

from services.sql_service import delete_chat_session, retrieve_chat_sessions
from util_functions.functions import get_module_session, get_user_info
from util_functions.oai_functions import convert_attachments, convert_content


history_bp = Blueprint('history', __name__)

@history_bp.route('/history/user', methods=['GET'])
def get_user_history():
    """
    Retrieves the user history of the currently selected module and logged in user.
    
    URL:
    - GET /history/user
    
    Returns:
        JSON response: A flask response object containing a status message and a list of ChatSession objects.
    
    Status Codes:
        200 OK: Retrieved user history.
        400 Bad Request: An error occurred while retrieving the history.
    """
    user_session = get_user_info()
    chat_sessions = retrieve_chat_sessions(user_id=user_session['Id'])
    
    if chat_sessions is None:
        return jsonify({'error': 'Failed to retrieve chat sessions.'}), 400
    if chat_sessions is []:
        return jsonify({'error': 'No chat sessions found for this user.'}), 404
    chat_sessions.reverse()
    
    return jsonify({'message': 'Retrieved user chat sessions.', 'data': chat_sessions}), 200

@history_bp.route('/history/dialog', methods=['GET'])
def get_chat_dialog():
    """
    Retrieves the dialog of an OpenAI thread and returns its contents.
    
    URL:
    - GET /history/dialog
    
    Parameters:
        thread_id (str): The ID of the thread the desired messages belong to.
    
    Returns:
        JSON response: A flask response object containing a status message and a list of message objects.
    
    Status Codes:
        200 OK: Messages retrieved.
        400 Bad Request: An error occurred while retrieving the messages.
    """
    thread_id = request.args.get('thread_id')
    if not thread_id:
        return jsonify({'error': 'Missing required fields.'}), 400
    thread_messages = client.beta.threads.messages.list(thread_id=thread_id)
    if thread_messages:
        messages_list = []
        for msg in thread_messages:
            message_dict = {
                'Id': msg.id,
                'Created': msg.created_at,
                'Role': msg.role,
                'Content': convert_content(msg.content),
                'Attachments': convert_attachments(msg.attachments)
            }
            messages_list.append(message_dict)
          
        messages_list.reverse()
        
        return jsonify({'message': 'Retrieved thread messages', 'messages': messages_list}), 200
    else:
        return jsonify({'error': 'Failed to obtain thread messages.'}), 400
    
@history_bp.route('/history/dialog', methods=['DELETE'])
def delete_chat_history():
    """
    Deletes a chat session by ID.
    
    URL:
    - DELETE /history/dialog
    
    Parameters:
        chat_id (str): The ID of the ChatSession to be deleted.
        
    Returns:
        JSON response: A flask response object containing a status message along with the ID of the deleted ChatSession.
        
    Status Codes:
        200 OK: ChatSession deleted.
        400 Bad Request: Failed to delete ChatSession
    """
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    deleted_id = delete_chat_session(chat_id=chat_id)
    if not deleted_id:
        return jsonify({'error': 'Failed to delete chat session.'}), 400
    else:
        return jsonify({'message': 'Deleted chat session', 'Id': deleted_id}), 200