from flask import jsonify
import tiktoken
import openai
import os
import json
from packaging import version
from config import OPENAI_CLIENT as client
import time

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

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
  # update_assistant_tokens(assistant_name, inp_tokens, inp_cost_tok, out_tokens,
  #                         out_cost_tok)
  
  return response


# def create_agent(agent_id):
#   file = f'agents/{agent_id}.json'

#   if os.path.exists(file):
#     with open(file, 'r') as file:
#       assistant_data = json.load(file)
#       assistant_id = assistant_data['assistant_id']
#       print("Loaded existing assistant ID")
#   else:
#     objections_file = client.files.create(file=open(
#         "Files/Namitkovnik - domlouvani analyzy.docx", "rb"),
#                                           purpose="assistants")
#     assistant = client.beta.assistants.create(name="ta_objections",
#                                               instructions=instructions,
#                                               model=model,
#                                               tools=[{
#                                                   "type": "retrieval"
#                                               }],
#                                               file_ids=[
#                                                   objections_file.id,
#                                               ])

#     with open(file, 'w') as file:
#       json.dump({'assistant_id': assistant.id}, file)
#       print('Created a new assistant and saved the ID')

#     assistant_id = assistant.id

#   return assistant_id