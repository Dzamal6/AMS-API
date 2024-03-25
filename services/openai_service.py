from flask import jsonify
import tiktoken
import openai
import os
import json
from packaging import version
from config import OPENAI_CLIENT as client
import time
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
  file = f'agents/{agent_id}.json'

  agent_data = get_agent_data(agent_id)

  if not agent_data or agent_data is None:
    return None

  if os.path.exists(file):
    with open(file, 'r') as file:
      agent_details = json.load(file)
      agent_id = str(agent_details['agent_id'])
      print("Loaded existing assistant ID")
  else:
    # objections_file = client.files.create(file=open(
    #     "Files/Namitkovnik - domlouvani analyzy.docx", "rb"),
    #                                       purpose="assistants")
    agent = client.beta.assistants.create(name=agent_data['name'],
                                              instructions=agent_data['system_prompt'],
                                              model=agent_data['model']
                                              # tools=[{
                                              #     "type": "retrieval"
                                              # }],
                                              # file_ids=[
                                              #     objections_file.id,
                                              # ]
                                             )

    if not os.path.exists('agents'):
      os.makedirs('agents')

    with open(file, 'w') as file:
      json.dump({'agent_id': agent.id}, file)
      print('Created a new assistant and saved the ID')

    agent_id = agent.id

  return agent_id

# TODO: delete agent files
def delete_agent(agent_id: str):
  agent_data = get_agent_data(agent_id)

  if not agent_data or agent_data is None:
    return None

  path = f'agents/{agent_id}.json'

  if not os.path.exists(path):
    return None

  with open(path, 'r') as file:
    agent_details = json.load(file)
    response = client.beta.assistants.delete(assistant_id=agent_details['agent_id'])

  if response.deleted:
    os.remove(path)
    return response.id
  else: 
    return None