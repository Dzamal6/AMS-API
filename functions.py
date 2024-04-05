from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import requests
import pytz
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, current_app
import hashlib
from config import user_session_serializer, assistant_session_serializer, chat_session_serializer
from functools import wraps
import bcrypt
from sqlalchemy.inspection import inspect
import os


def get_project_headers():
  assistant_session = get_assistant_session()
  token = ''
  if assistant_session:
    token = assistant_session['token']
  return {
      "accept": "application/json",
      "content-type": "application/json",
      "Authorization": f"{token}"
  }


def get_dialog_headers():
  assistant_session = get_assistant_session()
  token = ''
  if assistant_session:
    token = assistant_session['token']
  return {
    "accept": "application/json",
    "versionID": 'production',
    "content-type": "application/json",
    "Authorization": f"{token}"
  }

def validate_authorization_key(token):
  if token != os.environ['AGENT_AUTHORIZATION_KEY']: 
    return False
  return True

def transform_transcript_names(vf_transcripts, sql_transcripts):
  # TODO: If an sql_transcript is not found in vf_transcripts, delete the transcript
  
  for transcript in vf_transcripts:
    for sql_transcript in sql_transcripts:
      if transcript['sessionID'] == sql_transcript['SessionID']:
        transcript['name'] = sql_transcript['Username']
        break
        
  return vf_transcripts

def model_to_dict(model, include_relationships=False):
  model_dict = {c.key: getattr(model, c.key)
                for c in inspect(model).mapper.column_attrs}
  
  if include_relationships:
    for relationship in inspect(model).mapper.relationships:
        related_objects = getattr(model, relationship.key)
        if related_objects is not None:
          if relationship.uselist: 
            model_dict[relationship.key] = [model_to_dict(obj, include_relationships=False) for obj in related_objects]
          else:  
            model_dict[relationship.key] = model_to_dict(related_objects, include_relationships=False)

  for key, value in model_dict.items():
      if isinstance(value, datetime):
          model_dict[key] = value.isoformat()  
  
  return model_dict

def check_user_projects(projects, user_projects):
  out_projects = []
  for project in projects:
    if project['Id'] in [proj['Id'] for proj in user_projects]:
      out_projects.append(project)
  return out_projects

def check_assistant_permission(projectId):
  user_info = get_user_info()
  
  if user_info and any(a['Id'] == projectId for a in user_info['Assistants']):
    return True
  return False

def check_is_current_user(user_id):
  user_info = get_user_info()
  if user_info:
    return user_id == user_info['Id']

def get_chat_session():
  chat_session = request.cookies.get('chat_session')
  if chat_session:
    return chat_session_serializer.loads(chat_session)

def get_user_info():
  user_session = request.cookies.get('user_session')
  if user_session:
    return user_session_serializer.loads(user_session)

def get_assistant_session():
  assistant_session = request.cookies.get('assistant_session')
  if assistant_session:
    return assistant_session_serializer.loads(assistant_session)

def check_admin():
  user_session = get_user_info()
  if user_session:
    print(user_session['Roles'])
    return 'admin' in user_session['Roles'].lower()


def roles_required(*required_roles):

  def decorator(f):

    @wraps(
        f
    )  # preserves name and docstring of the function => distinguishes particular calls of decorator
    def wrapper(*args, **kwargs):
      user_session = request.cookies.get('user_session')
      if user_session:
        user_info = user_session_serializer.loads(user_session)
        user_roles = user_info['Roles']
        if not user_roles:
          return jsonify({'message': 'Invalid session.'}), 401
        if not any(required_role.lower() in (user_role['Name'].lower()
                                             for user_role in user_roles)
                   for required_role in required_roles):
          return jsonify({'message': 'Insufficient permissions.'}), 401
        return f(*args, **kwargs)
      else:
        return jsonify({'message': 'Invalid session.'}), 401

    return wrapper

  return decorator


def hash_password(password):
  hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
  return hashed.decode('utf-8')

def check_password(hashed, password):
  return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def encrypt_token(key, token):
  fernet = Fernet(key)
  return fernet.encrypt(token.encode()).decode()


def decrypt_token(key, encrypted_token):
  fernet = Fernet(key)
  return fernet.decrypt(encrypted_token.encode()).decode()


def convert_to_timezone(date_str, from_tz, to_tz):
  date = datetime.fromisoformat(date_str.rstrip('Z'))

  from_zone = pytz.timezone(from_tz)
  date = from_zone.localize(date)

  to_zone = pytz.timezone(to_tz)
  converted_date = date.astimezone(to_zone)

  return converted_date.isoformat()


def daterange(start, end):
  for n in range(int((end - start).days) + 1):
    yield start + timedelta(n)


def get_date_x_days_ago_isoformat(x):
  today_utc = datetime.utcnow()

  date_x_days_ago = today_utc - timedelta(days=x)

  return date_x_days_ago.strftime('%Y-%m-%dT00:00:00.000Z')


def get_endTime_of_day(date):
  date = datetime.strptime(date, '%Y-%m-%dT00:00:00.000Z')
  return date.strftime('%Y-%m-%dT23:59:59.000Z')


def fetch_data_for_type_and_date(endpoint, headers, project_id, data_type,
                                 date):
  payload = {
      'query': [{
          'name': data_type,
          'filter': {
              'projectID': project_id,
              'startTime': date,
              'endTime': get_endTime_of_day(date)
          }
      }]
  }
  response = requests.post(endpoint, json=payload, headers=headers)
  if response.status_code == 200:
    data = response.json()['result']
    return {'date': date, data_type: data}
  else:
    print(f'Could not retrieve data for {data_type} at {date}')
    return None


# Needs substantial efficiency optimization => 12 month period takes >5 minutes.
def retrieve_data(start, end, types, endpoint, headers, project_id):
  start_date = datetime.fromisoformat(start.rstrip('Z'))
  end_date = datetime.fromisoformat(end.rstrip('Z'))

  date_list = [
      single_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
      for single_date in daterange(start_date, end_date)
  ]

  data_for_graph = {data_type: [] for data_type in types}
  futures = []

  with ThreadPoolExecutor(max_workers=30) as executor:
    for data_type in types:
      for date in date_list:
        future = executor.submit(fetch_data_for_type_and_date, endpoint,
                                 headers, project_id, data_type, date)
        futures.append((future, data_type))

    for future, data_type in futures:
      result = future.result()
      if result:
        data_for_graph[data_type].append(result)

  return data_for_graph
