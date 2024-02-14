import json
import requests
import os
from openai import OpenAI
from config import OPENAI_API_KEY, TA_INSTRUCTIONS

client = OpenAI(api_key=OPENAI_API_KEY)

def create_ta_objections(client):
  file = 'Assistants/ta_objections.json'

  if os.path.exists(file):
    with open(file, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID")
  else:
    objections_file = client.files.create(file=open(
        "Files/Namitkovnik - domlouvani analyzy.docx", "rb"),
                                          purpose="assistants")
    assistant = client.beta.assistants.create(name="ta_objections",
                                              instructions=TA_INSTRUCTIONS,
                                              model="gpt-4-1106-preview",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[
                                                  objections_file.id,
                                              ])

    with open(file, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print('Created a new assistant and saved the ID')

    assistant_id = assistant.id

  return assistant_id


def create_ta_recommend(client):
  file = 'Assistants/ta_recommend.json'

  if os.path.exists(file):
    with open(file, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID")
  else:
    reccomend_call_file = client.files.create(file=open(
        "Files/telefonat_na_doporuceni.docx", "rb"),
                                              purpose="assistants")
    assistant = client.beta.assistants.create(name="ta_recommend",
                                              instructions=TA_INSTRUCTIONS,
                                              model="gpt-4-1106-preview",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[
                                                  reccomend_call_file.id,
                                              ])

    with open(file, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print('Created a new assistant and saved the ID')

    assistant_id = assistant.id

  return assistant_id


def create_ta_analysis_01(client):
  file = 'Assistants/ta_analysis_01.json'

  if os.path.exists(file):
    with open(file, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID")
  else:
    manual_analyses_01 = client.files.create(file=open(
        "Files/01_manual_predstaveni_sluzby_230419.docx", "rb"),
                                             purpose="assistants")
    assistant = client.beta.assistants.create(name="ta_analysis_01",
                                              instructions=TA_INSTRUCTIONS,
                                              model="gpt-4-1106-preview",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[
                                                  manual_analyses_01.id,
                                              ])

    with open(file, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print('Created a new assistant and saved the ID')

    assistant_id = assistant.id

  return assistant_id


def create_ta_analysis_02(client):
  file = 'Assistants/ta_analysis_02.json'

  if os.path.exists(file):
    with open(file, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID")
  else:
    manual_analyses_02 = client.files.create(file=open(
        "Files/02_manual_programy_230419.docx", "rb"),
                                             purpose="assistants")
    manual_analyses_03 = client.files.create(file=open(
        "Files/03_manual_SA_audit_230727.docx", "rb"),
                                             purpose="assistants")
    assistant = client.beta.assistants.create(name="ta_analysis_02",
                                              instructions=TA_INSTRUCTIONS,
                                              model="gpt-4-1106-preview",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[
                                                  manual_analyses_02.id,
                                              ])

    with open(file, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print('Created a new assistant and saved the ID')

    assistant_id = assistant.id

  return assistant_id


def create_ta_analysis_03(client):
  file = 'Assistants/ta_analysis_03.json'

  if os.path.exists(file):
    with open(file, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID")
  else:
    manual_analyses_03 = client.files.create(file=open(
        "Files/03_manual_SA_audit_230727.docx", "rb"),
                                             purpose="assistants")
    assistant = client.beta.assistants.create(name="ta_analysis_03",
                                              instructions=TA_INSTRUCTIONS,
                                              model="gpt-4-1106-preview",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[
                                                  manual_analyses_03.id,
                                              ])

    with open(file, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print('Created a new assistant and saved the ID')

    assistant_id = assistant.id

  return assistant_id