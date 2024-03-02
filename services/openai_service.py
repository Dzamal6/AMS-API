from flask import jsonify
import openai.assistants as opa
import openai
import tiktoken
import os
from packaging import version
import openaiw
from openai import OpenAI

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

client = OpenAI(api_key=OPENAI_API_KEY)

if current_version < required_version:
  raise ValueError(
      f"Error: OpenAI version {openai.__version__} is less than required version {required_version}. Please upgrade OpenAI to the latest version."
  )
else:
  print("OpenAI version is compatible")

def chat_ta(assistant_id, assistant_name, thread_id, user_input):
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
  update_assistant_tokens(assistant_name, inp_tokens, inp_cost_tok, out_tokens,
                          out_cost_tok)
  
  return response