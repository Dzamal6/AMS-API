from flask import Blueprint, jsonify
from openai import OpenAI
from config import OPENAI_API_KEY

openai_bp = Blueprint("openai", __name__)

client = OpenAI(api_key=OPENAI_API_KEY)


@openai_bp.route('/initialize', methods=['GET'])
def start_conversation():
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")
  return jsonify({"thread_id": thread.id})
