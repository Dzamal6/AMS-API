from flask import Blueprint, jsonify, request
from openai import OpenAI
from config import OPENAI_API_KEY
import time
import tiktoken
# from services.openai_service import chat_ta
from database.database import session_scope
import uuid
from database.models import Document

openai_bp = Blueprint("openai", __name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# TODO: auth token for endpoints called from voiceflow (exempt from session checks)

@openai_bp.route('/initialize', methods=['GET'])
def initialize():
  # agent_id = request.json.get('agent_id')
  print("Starting a new conversation...")
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")

  as_instructions = request.json.get('as_instructions')

  my_assistant = client.beta.assistants.create(
      instructions=as_instructions,
      name="brog",
      model="gpt-4",
  )

  return jsonify({'thread_id': thread.id}), 200


# Temporary assistant. Delete when the actual openai Endpoints are finished.
@openai_bp.route('/chat', methods=['POST'])
def chat():

  assistant_id = 'asst_DrK1j2mtfTa5pJfS3hwJP0qY'
  thread_id = request.json.get('thread_id')
  user_input = request.json.get('message')

  print(user_input, thread_id, assistant_id)
  # Token Counting Input
  encoding = tiktoken.get_encoding("cl100k_base")
  encoding = tiktoken.encoding_for_model("gpt-4")
  
  inp_tokens = len(encoding.encode(user_input))
  inp_cost_tok = (0.01 / 1000) * inp_tokens
  print(
      f"Number of tokens input: {inp_tokens}\nCost of tokens: {inp_cost_tok}")
  
  if not thread_id:
    print('Error: Missing thread_id')
    return jsonify({'error': 'missing thread_id'}), 400
  
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
      return jsonify({'error': 'timeout'}), 400
  
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
                          # out_cost_tok)
  
  return jsonify({'response': response})