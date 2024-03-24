from flask import Blueprint, jsonify, request
from openai import OpenAI
from config import OPENAI_CLIENT as client
import time
import tiktoken
# from services.openai_service import chat_ta
from database.database import session_scope
import uuid
from database.models import Document
from functions import validate_authorization_key
from services.sql_service import get_agent_data
from services.openai_service import chat_ta

openai_bp = Blueprint("openai", __name__)

@openai_bp.route('/openai/initialize_dev', methods=['GET'])
def initialize_dev():
  # agent_id = request.json.get('agent_id')
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")

  agent_id = request.json.get('agent_id')
  agent = get_agent_data(agent_id)

  assistant = client.beta.assistants.create(
      instructions=agent['system_prompt'],
      name="brog",
      model="gpt-4",
  )

  assistant_id = assistant.id
  print(f"New assistant created with ID: {assistant_id}")

  return jsonify({'thread_id': thread.id}), 200

# On chat initialize
# def create_agent():
  

# Temporary endpoint for testing purposes
@openai_bp.route('/initialize', methods=['GET'])
def initialize():
  auth_key = request.headers.get('Authorization')
  auth = validate_authorization_key(auth_key)

  if not auth_key or not auth:
    return jsonify({'error': 'Unauthorized'}), 401
  
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")
  return jsonify({"thread_id": thread.id})

# Temporary assistant. Delete when the actual openai Endpoints are finished.
# @openai_bp.route('/chat', methods=['POST'])
# def chat():
#   auth_key = request.headers.get('Authorization')
#   auth = validate_authorization_key(auth_key)

#   if not auth_key or not auth:
#     return jsonify({'error': 'Unauthorized'}), 401
  
#   assistant_id = 'asst_DrK1j2mtfTa5pJfS3hwJP0qY'
#   thread_id = request.json.get('thread_id')
#   user_input = request.json.get('message')

#   print(user_input, thread_id, assistant_id)

#   chat = chat_ta(assistant_id, )
  