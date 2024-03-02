from flask import Blueprint, jsonify, request
from openai import OpenAI
from config import OPENAI_API_KEY
import time
import tiktoken
from services.openai_service import chat_ta
from database.database import session_scope
import uuid
from database.models import Document

openai_bp = Blueprint("openai", __name__)

client = OpenAI(api_key=OPENAI_API_KEY)

@openai_bp.route('/initialize', methods=['GET'])
def start_conversation():
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")
  
  tp = request.json.get("type", None)
  files = request.json.get("files", None)
  
  if not tp:
    return jsonify({"error": "You need to pass a type"}), 400
  elif tp == "objections":
    with session_scope() as session:
      for file_hash in files:
        file_in_db 
    
