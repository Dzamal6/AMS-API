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
  """
  Retrieves HTTP headers necessary for making API requests to a project-specific endpoint, including authorization token.

  Returns:
      dict: Headers including Content-Type, Accept, and Authorization populated with the user's token.
  """
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
  """
  Retrieves HTTP headers necessary for interacting with dialog endpoints, including authorization token and version information.

  Returns:
      dict: Headers including Content-Type, Accept, VersionID set to 'production', and Authorization populated with the user's token.
  """
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
  """
  Validates the provided authorization token against the environment's expected authorization key.

  Parameters:
      token (str): The token to validate.

  Returns:
      bool: True if the token matches the environment's authorization key, False otherwise.
  """
  if token != os.environ['AGENT_AUTHORIZATION_KEY']: 
    return False
  return True

def transform_transcript_names(vf_transcripts, sql_transcripts):
  """
  Matches Voiceflow transcripts with SQL transcripts by session ID and updates the name in Voiceflow transcripts to the username from SQL transcripts.

  Parameters:
      vf_transcripts (list of dict): List of transcripts from Voiceflow.
      sql_transcripts (list of dict): List of transcripts from SQL database.

  Returns:
      list of dict: The updated list of Voiceflow transcripts with usernames from the SQL database.
  """
  # TODO: If an sql_transcript is not found in vf_transcripts, delete the transcript
  
  for transcript in vf_transcripts:
    for sql_transcript in sql_transcripts:
      if transcript['sessionID'] == sql_transcript['SessionID']:
        transcript['name'] = sql_transcript['Username']
        break
        
  return vf_transcripts

def model_to_dict(model, include_relationships=False):
  """
  Converts an SQLAlchemy model instance into a dictionary, optionally including related objects.

  Parameters:
      model (SQLAlchemy Model): The model instance to convert.
      include_relationships (bool): If True, includes the data from related objects.

  Returns:
      dict: A dictionary representation of the model instance.
  """
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
  """
  Filters a list of projects to include only those that exist in a user's project list.

  Parameters:
      projects (list of dict): List of all projects.
      user_projects (list of dict): List of the user's projects.

  Returns:
      list of dict: Filtered list of projects that are included in the user's project list.
  """
  out_projects = []
  for project in projects:
    if project['Id'] in [proj['Id'] for proj in user_projects]:
      out_projects.append(project)
  return out_projects

def check_assistant_permission(projectId):
  """
  Checks if the current user has permission to access a specific project based on their assistants' IDs.

  Parameters:
      projectId (str): The project ID to check permissions for.

  Returns:
      bool: True if the user has permission, False otherwise.
  """
  user_info = get_user_info()
  
  if user_info and any(a['Id'] == projectId for a in user_info['Assistants']):
    return True
  return False

def check_is_current_user(user_id):
  """
  Checks if the provided user ID matches the current user's ID.

  Parameters:
      user_id (str): The user ID to check.

  Returns:
      bool: True if the provided user ID matches the current user's ID, False otherwise.
  """
  user_info = get_user_info()
  if user_info:
    return user_id == user_info['Id']

def get_chat_session():
  """
  Retrieves the chat session data from cookies.

  Returns:
      any: The deserialized chat session data or None if no chat session is present in cookies.
  """
  chat_session = request.cookies.get('chat_session')
  if chat_session:
    return chat_session_serializer.loads(chat_session)

def get_user_info():
  """
  Retrieves the user info from cookies.

  Returns:
      dict: The deserialized user info data or None if no user session is present in cookies.
  """
  user_session = request.cookies.get('user_session')
  if user_session:
    return user_session_serializer.loads(user_session)

def get_assistant_session():
  """
  Retrieves the assistant session data from cookies.

  Returns:
      dict: The deserialized assistant session data or None if no assistant session is present in cookies.
  """
  assistant_session = request.cookies.get('assistant_session')
  if assistant_session:
    return assistant_session_serializer.loads(assistant_session)

def check_admin():
  """
  Checks if the current user has an 'admin' role.

  Returns:
      bool: True if the user is an admin, False otherwise.
  """
  user_session = get_user_info()
  if user_session:
    print(user_session['Roles'])
    return any(role['Name'].lower() == 'admin' for role in user_session.get('Roles', []))


def roles_required(*required_roles):
  """
  Decorator to check if the current user has at least one of the specified roles.

  Parameters:
      *required_roles (str): Roles required to execute the function.

  Returns:
      function: A wrapper function that either proceeds with the execution if roles match or returns an error.
  """

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
  """
  Hashes a password using bcrypt.

  Parameters:
      password (str): The password to hash.

  Returns:
      str: The hashed password.
  """
  hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
  return hashed.decode('utf-8')

def check_password(hashed, password):
  """
  Checks a password against a hashed value using bcrypt.

  Parameters:
      hashed (str): The hashed password.
      password (str): The plaintext password to check.

  Returns:
      bool: True if the password matches the hash, False otherwise.
  """
  return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def encrypt_token(key, token):
  """
  Encrypts a token using Fernet symmetric encryption.

  Parameters:
      key (bytes): The key used for encryption.
      token (str): The token to encrypt.

  Returns:
      str: The encrypted token.
  """
  fernet = Fernet(key)
  return fernet.encrypt(token.encode()).decode()


def decrypt_token(key, encrypted_token):
  """
  Decrypts a token using Fernet symmetric encryption.

  Parameters:
      key (bytes): The key used for decryption.
      encrypted_token (str): The encrypted token to decrypt.

  Returns:
      str: The decrypted token.
  """
  fernet = Fernet(key)
  return fernet.decrypt(encrypted_token.encode()).decode()
