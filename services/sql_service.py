import logging
from database.database import SessionLocal, session_scope
from database.models import Module, User, Role, ChatSession, Transcript, Document, Agent, agent_file_table, document_module_table
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
import uuid
from flask import jsonify
from datetime import datetime
from util_functions.sql_functions import associate_modules, check_for_duplicate, compute_file_hash, create_default_agents, get_doc_content, get_module, get_modules_as_dicts, get_roles_as_dicts, get_user_name
from util_functions.functions import hash_password, is_email
from werkzeug.utils import secure_filename
import os
import hashlib
import io
from typing import cast
from psycopg2.errors import InvalidTextRepresentation

def get_module_by_id(module_id: str):
  """
  Retrieves module details by module ID.

  Parameters:
      module_id (str): The unique identifier for the module.

  Returns:
      dict or None: A dictionary containing the module's details if found, None otherwise.
  """
  try:
    with session_scope() as session:
      module = session.query(Module).filter_by(id=module_id).first()
      if module:
        return {
            'Id': str(module.id),
            'Name': module.name,
            'Voice': module.voice,
            'Analytics': module.convo_analytics,
            'Summaries': module.summaries,
            'Created': module.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        }
      else:
        return None
  except SQLAlchemyError as e:
    print(f"Database Error: {e}")
    return jsonify({'message': "Module could not be resolved."}), 400

  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500
  

def get_all_modules():
  """
  Retrieves all available modules from the database.
  
  Returns:
      list of dict or None: A list of dictionaries representing all modules, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      modules_query = session.query(Module).all()
      modules = [{
        'Id': str(module.id),
        'Name': module.name,
        'Description': module.description,
        'FlowControl': module.flow_control,
        'Voice': module.voice,
        'ConvoAnalytics': module.convo_analytics,
        'Summaries': module.summaries,
        'Created': module.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': module.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for module in modules_query]
      return modules
  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500
  

def create_new_module(
  name: str, 
  description: str="None", 
  flow_control: str="User", 
  voice: bool=False, 
  convo_analytics: bool=False, 
  summaries: bool=False ):
  """
  Creates a new module in the database.
  
  Parameters:
    name (str): The name of the new module.
    description (str): The description of the new module.
    flow_control (str): If the module conversations should be directed by AI or the user. The field accepts 'AI' for setting the module to be directed by AI and 'User' to set the module to be directed by the user. This is used e.g. when the user gives tasks that the module's AIs complete or when the user is not supposed to direct the conversation (trainings, interviews where the AI is interviewing the user). If not set, 'User' is assumed by default.
    voice (bool): Whether the module conversations should be conducted via tts and stt or not. False by default.
    convo_analytics (bool): Whether the module will analyze each saved conversation using AI. False by default.
    summaries (bool): Whether the module will create a short summary of each saved conversation using AI. False by default.
    
  Returns:
    JSON and literal: A JSON object containing the success literal and module details, or an error literal if an error occurs.
  """
  try:
    with session_scope() as session:
      existing_module = session.query(Module).filter(
        Module.name == name).first()
      
      if existing_module is not None:
        print(f"Module '{name}' already exists.")
        return 'Module already exists', 409
      
      id = uuid.uuid4()
      new_module = Module(id=id,
                        name=name,
                        description=description,
                        flow_control=flow_control,
                        voice=voice,
                        convo_analytics=convo_analytics,
                        summaries=summaries)
      session.add(new_module)
      session.commit()
      
      create_default_agents(module_id=str(new_module.id), session=session, flow_control=flow_control, analytics=convo_analytics, summaries=summaries)
      
      module_data = {
        'Id': str(new_module.id),
        'Name': new_module.name,
        'Description': new_module.description,
        'FlowControl': new_module.flow_control,
        'Voice': new_module.voice,
        'ConvoAnalytics': new_module.convo_analytics,
        'Summaries': new_module.summaries,
        'Created': new_module.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': new_module.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
      return module_data, 201
  except Exception as e:
    print(f"An error occurred: {e}")
    return None, 400
  

def update_module(
  module_id: str,
  name: str=None, 
  description: str=None, 
  flow_control: str=None, 
  voice: bool=None, 
  convo_analytics: bool=None, 
  summaries: bool=None):
  """
  Updates a module in the database. Existing ChatSessions are not updated. If `summaries` or `analytics` is changed
  here, the existing ChatSessions remain configured with the previous module settings.
  
  Parameters:
    module_id (str): The ID of the module to be updated.
    name (str): The name of the module.
    description (str): The description of the module.
    flow_control (str): If the module conversations should be directed by AI or the user. The field accepts 'AI' for setting the module to be directed by AI and 'User' to set the module to be directed by the user. This is used e.g. when the user gives tasks that the module's AIs complete or when the user is not supposed to direct the conversation (trainings, interviews where the AI is interviewing the user). If not set, 'User' is assumed by default.
    voice (bool): Whether the module conversations should be conducted via tts and stt or not.
    convo_analytics (bool): Whether the module will analyze each saved conversation using AI.
    summaries (bool): Whether the module will create a short summary of each saved conversation using AI.
  
  Returns:
    dict: The updated ChatSession object or None if the operation fails.
  """
  try:
    with session_scope() as session:
      module = session.query(Module).filter(Module.id == module_id).first()
      
      if module is None:
        logging.error(f'Module {module_id} not found.')
        return None

      updated_fields = []

      if name is not None and name != module.name:
        module.name = name
        updated_fields.append('name')
      if description is not None and description != module.description:
        module.description = description
        updated_fields.append('description')
      if flow_control is not None and flow_control != module.flow_control:
        module.flow_control = flow_control
        updated_fields.append('flow_control')
      if voice is not None and voice != module.voice:
        module.voice = voice
        updated_fields.append('voice')
      if convo_analytics is not None and convo_analytics != module.convo_analytics:
        module.convo_analytics = convo_analytics
        updated_fields.append('convo_analytics')
      if summaries is not None and summaries != module.summaries:
        module.summaries = summaries
        updated_fields.append('summaries')
      
      if updated_fields:
        session.commit()
        logging.info(f'Module {module_id} updated. Fields changed: {", ".join(updated_fields)}')
      else:
        logging.info(f'No changes made to Module {module_id}.')

      return {
        'Id': str(module.id),
        'Name': module.name,
        'Description': module.description,
        'FlowControl': module.flow_control,
        'Voice': module.voice,
        'ConvoAnalytics': module.convo_analytics,
        'Summaries': module.summaries,
        'Created': module.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': module.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
  except SQLAlchemyError as e:
    logging.error(f'SQLAlchemy error updating module {module_id}. {e}')
    return None
  except Exception as e:
    logging.error(f'Error updating module {module_id}. {e}')
    return None

    

def delete_module(module_id: str):
  """
  Deletes a module from the database.
  
  Parameters:
    module_id (str): The unique identifier of the module to be deleted.
    
  Returns:
    str or None: The unique identifier of the deleted module or None if the deletion failed.
  """
  try:
    with session_scope() as session:
      module = session.query(Module).filter(Module.id == module_id).first()
      
      if not module:
                logging.error(f'Module with ID: {module_id} not found.')
                return None
              
      orphaned_documents = []
      for document in module.documents:
        other_modules = session.query(Module).join(Module.documents).filter(Document.id == document.id).filter(Module.id != module_id).all()
        if not other_modules:
          orphaned_documents.append(document)
          
      for document in orphaned_documents:
        session.delete(document)
      
      session.delete(module)
      session.commit()
      
      return module_id
  except SQLAlchemyError as e:
    logging.error(f'Failed to delete module with ID: {module_id}. {e}')
    return None
  except Exception as e:
    logging.error(f'Failed to delete module with ID: {module_id}. {e}')
    return None


def add_user(email, roles, modules):
  """
  Adds a new user with specified roles and modules to the database.

  Parameters:
      username (str): The username for the new user.
      password (str): The password for the new user.
      roles (list of str): A list of role IDs that the user will be associated with.
      modules (list of str): A list of module IDs that the user will be associated with.

  Returns:
      JSON or None: A JSON object containing the registration details and success message, or an error message if the registration fails.
  """
  id = str(uuid.uuid4())
  
  print('creating user')

  try:
    with session_scope() as session:
      roles_uuids = [uuid.UUID(role_id) for role_id in roles]
      module_uuids = [uuid.UUID(module_id) for module_id in modules]
      new_user = User(id=id,
                      email=email,
                      roles=session.query(Role).filter(
                          Role.id.in_(roles_uuids)).all(),
                      modules=session.query(Module).filter(
                          Module.id.in_(module_uuids)).all())

      session.add(new_user)
      session.commit()

      return jsonify({
          "message": "User created successfully.",
          "response": {
              "Id":
              id,
              "Created":
              new_user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
              "LastModified":
              new_user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
              "Email":
              new_user.email,
              "Roles":
              get_roles_as_dicts(new_user.roles),
              "Modules":
              get_modules_as_dicts(new_user.modules)
          }
      }), 200

  except SQLAlchemyError as e:
    print(f"Error: {e}")
    return jsonify({'message': "Failed to create user."}), 400
  except Exception as e:
    print(f"Error when creating user: {e}")
    return jsonify({'message': "Failed to create user."}), 400
  

def register_user(username: str, email: str, password_hash: str):
  try:
    with session_scope() as session:
      user = session.query(User).filter_by(email=email).first()
      
      if user.username or user.password_hash:
        logging.warning(f'Attempt to register existing account: {user.email}')
        return None
      user.username = username
      user.password_hash = password_hash
      
      session.commit()
      
      registered_user = {
        "Id": str(user.id),
        "Username": user.username,
        "Email": user.email,
        "Created": user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "Roles":
        get_roles_as_dicts(user.roles),
        "Modules":
        get_modules_as_dicts(user.modules)
      }
      
      return registered_user
  except SQLAlchemyError as e:
    print(f"Error: {e}")
    return None
  except Exception as e:
    print(f"Error: {e}")
    return None


def remove_user(user_id):
  """
  Removes a user from the database based on user ID.

  Parameters:
      user_id (str): The unique identifier of the user to be removed.

  Returns:
      JSON or None: A JSON object containing the success message and user ID, or an error message if the user is not found or another error occurs.
  """
  try:
    with session_scope() as session:
      user = session.query(User).filter(User.id == user_id).one()

      session.delete(user)
      session.commit()

      return jsonify({
          'message': 'User removed successfully',
          'user': {
              'id': user.id
          }
      }), 200
  except NoResultFound:
    return jsonify({'message': 'User not found'}), 404
  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500


def check_user_exists(email:str=None, id:str=None):
  """
  Checks if a user exists in the database based on the user email or id.

  Parameters:
      email (str): The email of the user to be checked.
      id (str): The ID of the user to be checked.

  Returns:
      bool or None: True if the user exists, False otherwise. If neither email or id is provided, None is returned.
  """
  try:
    with session_scope() as session:
      if id is not None:
        user = session.query(User).filter(User.id == id).first()
        if user is None or not user:
          return False
        return True
      elif email is not None:
        result = session.query(User).filter_by(email=email).first()
        if result is None or not result:
          return False
        return True
      elif email is None and id is None:
        logging.error('[check_user_exists()] - Missing required fields.')
        return None
  except Exception as e:
    print(f"Error: {e}")
    return False


def get_all_roles():
  """
  Retrieves all roles from the database.

  Returns:
      list of dict or None: A list of dictionaries representing all roles, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      roles_query = session.query(Role).all()
      roles = [{"Id": str(role.id), "Name": role.name} for role in roles_query]
      return roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user_roles(user_roles_ids):
  """
  Retrieves specific roles based on a list of role IDs.

  Parameters:
      user_roles_ids (list of str): A list of role IDs.

  Returns:
      list of dict or None: A list of dictionaries representing the roles, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      roles = session.query(Role).filter(Role.id.in_(user_roles_ids)).all()
      user_roles = [{"Id": str(role.id), "Name": role.name} for role in roles]
      return user_roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []
  
def get_user_modules(user_modules_ids):
  """
  Retrieves specific modules based on a list of module IDs.

  Parameters:
      user_modules_ids (list of str): A list of module IDs.

  Returns:
      list of dict or None: A list of dictionaries representing the modules, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      modules = session.query(Module).filter(
          Module.id.in_(user_modules_ids)).all()
      user_modules = [{
          "Id": str(module.id),
          "Name": module.name
      } for module in modules]
      return user_modules
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_all_users():
  """
  Retrieves all users from the database along with their associated roles and modules.

  Returns:
      list of dict or None: A list of dictionaries representing all users, their roles, and modules, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      users = session.query(User).all()

      all_roles = session.query(Role).all()
      all_modules = session.query(Module).all()

      roles_dict = {role.id: role for role in all_roles}
      modules_dict = {
          module.id: module
          for module in all_modules
      }

      users_data = []
      for user in users:
        user_roles_ids = [role.id for role in user.roles]
        user_modules_ids = [module.id for module in user.modules]

        user_roles = [{
            "Id": str(role.id),
            "Name": role.name
        } for role_id in user_roles_ids for role in (roles_dict.get(role_id), )
                      if role]
        user_modules = [
            {
                "Id": str(module.id),
                "Name": module.name
            } for module_id in user_modules_ids
            for module in (modules_dict.get(module_id), ) if module
        ]

        users_data.append({
            "Id":
            str(user.id),
            "Username":
            user.username,
            "Email": 
            user.email,
            "Roles":
            user_roles,
            "Modules":
            user_modules,
            "Created":
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified":
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        })
      return users_data
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user(credential: str):
  """
  Retrieves a user by email or username from the database.

  Parameters:
      credential (str): The email or username of the user to be retrieved.

  Returns:
      dict or None: A dictionary containing the user's details if found, or an empty dictionary if the user is not found, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      if is_email(credential):
        user = session.query(User).filter(User.email == credential).first()
      else:
        user = session.query(User).filter(User.username == credential).first()

      if user:
        user_data = {
            'Id':
            str(user.id),
            'Username':
            user.username,
            'Email':
            user.email,
            'Roles':
            get_user_roles([role.id for role in user.roles]),
            'Modules': 
            get_user_modules([module.id for module in user.modules]),
            'password_hash':
            user.password_hash,
            'Created':
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            'LastModified':
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }

        return user_data
      else:
        return None
  except Exception as e:
    print(f"An error occured: {e}")
    return None
  

def update_user(user_id,
                username=None,
                password=None,
                roles=None,
                modules=None):
  """
  Updates a user's details in the database.

  Parameters:
      user_id (str): The unique identifier of the user to be updated.
      username (str, optional): The new username for the user.
      password (str, optional): The new password for the user.
      roles (list of str, optional): A list of new role IDs to be associated with the user.
      modules (list of str, optional): A list of new module IDs to be associated with the user.

  Returns:
      dict or None: A dictionary containing the updated user's details if the update is successful, or None if the user is not found or an error occurs.
  """

  try:
    with session_scope() as session:
      user = session.query(User).filter(User.id == user_id).first()

      if user:
        if username is not None:
          user.username = username
        if password is not None:
          user.password_hash = password
        if roles is not None:
          print(roles)
          roles_uuids = [uuid.UUID(role_id) for role_id in roles]
          print(roles_uuids)
          user.roles = session.query(Role).filter(
              Role.id.in_(roles_uuids)).all()
          print(get_roles_as_dicts(user.roles))
        if modules is not None:
          modules_uuids = [
              uuid.UUID(module_id) for module_id in modules
          ]
          user.modules = session.query(Module).filter(
              Module.id.in_(modules_uuids)).all()

        current_time = datetime.now()
        session.commit()

        updated_user = {
            "Id": str(user.id),
            "Created": user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified": current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "Username": user.username,
            "Email": user.email,
            "Roles": get_roles_as_dicts(user.roles),
            "Modules": get_modules_as_dicts(user.modules)
        }

        return updated_user
      else:
        print(f"User with ID {user_id} not found")
        return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def upload_files(files, module_ids: list[str]=None):
  """
  Uploads files to the database, checking for duplicates based on file content hash.

  Parameters:
      files (list): A list of file objects to be uploaded.

  Returns:
      list of tuple: A list containing the results for each file upload attempt. Each tuple contains a status ('success' or 'error') and a dictionary with relevant information.
  """
  responses = []
  files_with_ids = {str(uuid.uuid4()): file for file in files}

  try:
    with session_scope() as session:
      file_data = [(file_id, doc, doc.filename, compute_file_hash(doc), get_doc_content(doc)) for file_id, doc in files_with_ids.items()]
      hashes = [f[3] for f in file_data]
      existing_docs = check_for_duplicate(hashes, session)

      for file_id, doc, filename, doc_hash, doc_content in file_data:
        if doc_hash in existing_docs:
          existing_doc = existing_docs[doc_hash]
          print(f"Duplicate found, including existing file in response: {existing_doc.id}")
          if module_ids is not None:
            associate_modules(existing_doc, module_ids, session)
          responses.append(('success', {
              'message': f'Duplicate document found for file {file_id}, including existing file.',
              "Id": existing_doc.id,
              "Name": existing_doc.name,
              "Content_hash": existing_doc.content_hash,
              "Created": existing_doc.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
              "LastModified": existing_doc.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
          }))
          continue

        document = Document(id=file_id, name=filename, content_hash=doc_hash, content=doc_content)
        if module_ids is not None:
          modules = session.query(Module).filter(Module.id.in_(module_ids)).all()
          document.modules = modules
          
        session.add(document)
        session.commit()
        responses.append(('success', {
            "Id": document.id,
            "Name": document.name,
            "Content_hash": document.content_hash,
            "Created": document.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified": document.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }))

  except Exception as e:
      print(f"An error occurred: {e}")
      responses.append(('error', {'error': f'An error occurred during upload. {str(e)}'}))

  return responses


def get_all_files(module_id: str):
  """
  Retrieves all files related to the set module from the database.

  Parameters:
      module_id (string): The unique identifier of the selected module.

  Returns:
      list of dict or None: A list of dictionaries representing all stored files, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      docs = session.query(Document).join(Document.modules).filter(Module.id == module_id).all()
      return [{
          "Id":
          str(doc.id),
          "Name":
          doc.name,
          "Created":
          doc.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
          "LastModified":
          doc.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for doc in docs]
  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def delete_doc(docId, module_id: str):
  """
    Deletes a specific document from the database or removes a module's association
    with that document based on the document's ID and the provided module ID.

    Parameters:
        docId (str): The unique identifier of the document to be deleted.
        module_id (str): The ID of the module for whom the document association should be removed.

    Returns:
        str or None: The ID of the deleted document if successful, or None otherwise.
    """
  try:
    with session_scope() as session:
      document = session.query(Document).filter_by(id=docId).first()
      if not document:
        print(f"Document with ID {docId} not found")
        return None

      if len(document.modules) > 1:
        assoc_query = session.query(document_module_table).filter(
          document_module_table.c.document_id == docId,
          document_module_table.c.module_id == module_id)
        assoc_entry = assoc_query.first()
        if assoc_entry:
            assoc_query.delete()
            session.commit()
            print(f"Removed association for module ID {module_id} from document ID {docId}")
        else:
            print(f"No association found for module ID {module_id} with document ID {docId}")
        return docId
      else:
        session.delete(document)
        session.commit()
        print(f"Deleted document with ID {docId}")
        return docId
  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def get_file(docId):
  """
  Retrieves a specific document's details from the database based on its ID.

  Parameters:
      docId (str): The unique identifier of the document to retrieve.

  Returns:
      dict or None: A dictionary containing the document's details if found, None otherwise.
  """
  try:
    with session_scope() as session:
      result = session.query(Document).filter_by(id=docId).first()
      if result:
        return {
          "Id":str(result.id),
          "Name":result.name,
          "Content_Hash":result.content_hash,
          "Content": result.content,
          "Created":result.created,
          "LastModified":result.last_modified
        }
      else:
        print(f"Document with ID {docId} not found")
        return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def get_filesIO_by_id(docIds):
  """
  Retrieves file content as IO streams for specified document IDs.

  Parameters:
      docIds (list of str): A list of document IDs for which to retrieve content.

  Returns:
      list of io.BytesIO or None: A list of io.BytesIO streams containing the file content, or None if no documents are found or an error occurs.
  """
  try:
    with session_scope() as session:
      result = session.query(Document).filter(Document.id.in_(docIds)).all()
      if result:
        blobs = []
        for file in result:
          content_bytes = cast(bytes, file.content)
          blobs.append(io.BytesIO(content_bytes))

        return blobs
      else:
        print(f'Files with ids {docIds} not found')
        return None
        
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def get_agent_data(agentId):
  """
  Retrieves detailed information and associated documents for a specific agent based on the agent's ID.

  Parameters:
      agentId (str): The unique identifier of the agent to retrieve data for.

  Returns:
      dict or None: A dictionary containing the agent's details and documents if found, None otherwise.
  """
  try:
    with session_scope() as session:
      agent = session.query(Agent).filter_by(id=agentId).first()
      if not agent:
        return None

      docs = []
      for file in agent.documents:
        content_bytes = cast(bytes, file.content)
        docs.append({'name': file.name, 'bytes': io.BytesIO(content_bytes)})

      agent_dict = {
        "Id": str(agent.id),
        "Name": agent.name,
        "Model": agent.model,
        "Instructions": agent.system_prompt,
        "Description": agent.description,
        "WrapperPrompt": agent.wrapper_prompt,
        "InitialPrompt": agent.initial_prompt,
        "AgentPointer": str(agent.agent_id_pointer),
        "Director": agent.director,
        "PromptChaining": agent.prompt_chaining,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in agent.documents],
        "Documents_IO": docs,
        "Created": agent.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": agent.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
      return agent_dict
  except InvalidTextRepresentation as e:
    print(f'Invalid input! {e}')
    return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def upload_agent_metadata(agent_details: dict[str, str],
                          module_id: str, document_ids: list[str]=None):
  """
  Creates a new agent in the database with specified details and associations to modules and documents.

  Parameters:
      agent_details (dict[str, str]): A dictionary containing the agent's details such as name, system prompt, and description.
      module_id (str): A list of modules IDs to associate with the agent.
      document_ids (list of str): A list of document IDs to associate with the agent.

  Returns:
      dict or None: A dictionary containing the newly created agent's details, or None if an error occurs.
  """
  try:
    with session_scope() as session:
      new_agent = Agent(id=uuid.uuid4(),
                        name=agent_details['name'],
                        system_prompt=agent_details['system_prompt'],
                        wrapper_prompt=agent_details['wrapper_prompt'],
                        initial_prompt=agent_details['initial_prompt'],
                        description=agent_details['description'],
                        agent_id_pointer=None if agent_details['agent_pointer'] == '' else uuid.UUID(agent_details['agent_pointer']),
                        model=agent_details['model'],
                        module_id=uuid.UUID(module_id))
      module = session.query(Module).filter(
          Module.id == module_id).first()
      new_agent.module = module

      if document_ids is not [] and not None:
        documents = session.query(Document).filter(
            Document.id.in_(document_ids)).all()
        new_agent.documents = documents

      session.add(new_agent)
      session.commit()

      return {
          "Id": str(new_agent.id),
          "Name": new_agent.name,
          "Model": new_agent.model,
          "Instructions": new_agent.system_prompt,
          "WrapperPrompt": new_agent.wrapper_prompt,
          "InitialPrompt": new_agent.initial_prompt,
          "AgentPointer": str(new_agent.agent_id_pointer),
          "Description": new_agent.description,
          "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in new_agent.documents],
          "Created": new_agent.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
          "LastModified": new_agent.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }

  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def retrieve_all_agents(module_id: str):
  """
  Retrieves all agents related to the selected module from the database.

  Parameters:
    module_id (str): The ID of the module to filter agents by.

  Returns:
      list of dict or None: A list of dictionaries representing all agents, or None if an error occurs.

  Access Control:
      Requires a module to be set prior to its call.
  """
  try:
    with session_scope() as session:
      agents = session.query(Agent).join(Agent.module).filter(Module.id == module_id).all()
      
      return [{
        "Id": str(agent.id),
        "Name": agent.name,
        "Model": agent.model,
        "Instructions": agent.system_prompt,
        "Description": agent.description,
        "WrapperPrompt": agent.wrapper_prompt,
        "InitialPrompt": agent.initial_prompt,
        "AgentPointer": str(agent.agent_id_pointer),
        "Director": agent.director,
        "Summarizer": agent.summarizer,
        "Analytic": agent.analytic,
        "PromptChaining": agent.prompt_chaining,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in agent.documents],
        "Created": agent.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": agent.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for agent in agents]

  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def delete_agent(agent_id):
  """
  Deletes a specific agent from the database based on the agent's ID.

  Parameters:
      agent_id (str): The unique identifier of the agent to be deleted.

  Returns:
      str or None: The ID of the deleted agent if successful, None otherwise.
  """
  try:
    with session_scope() as session:
      # obtain agent from db and delete associated files before deleting it
      result = session.query(Agent).filter_by(id=agent_id).first()
      if result:
        session.delete(result)
        session.commit()
        print(f"Deleted agent with ID {agent_id}")
        return agent_id
      else:
        print(f"Agent with ID {agent_id} not found")
        return None

  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def update_agent(agent_id, name, description, instructions, wrapper_prompt, initial_prompt, agent_pointer, model, document_ids):
  """
  Updates an existing agent's details in the database.

  Parameters:
      agent_id (str): The unique identifier of the agent to be updated.
      name (str): The new name for the agent.
      description (str): A new description of the agent.
      instructions (str): Updated system instructions for the agent.
      wrapper_prompt (str): A prompt that is set to be sent to the LLM with each user message. It acts as a 'wrapper' for user messages.
      initial_prompt (str): A prompt that is set to be sent to the LLM when it is initialized. May act as an 'opening' set of instructions.
      agent_pointer (str): The ID of the agent that the current agent will switch to when it completes its task.
      model (str): The model identifier for the agent.
      document_ids (list of str): A list of new document IDs to associate with the agent.

  Returns:
      dict or None: A dictionary containing the updated agent's details if successful, None otherwise.
  """
  try:
    with session_scope() as session:
      result = session.query(Agent).filter_by(id=uuid.UUID(agent_id)).first()
      if not result:
        return None

      if document_ids is not []:
        documents = session.query(Document).filter(
            Document.id.in_(document_ids)).all()
        result.documents = documents
        
      result.name = name
      result.description = description
      result.system_prompt = instructions
      result.wrapper_prompt = wrapper_prompt
      result.initial_prompt = initial_prompt
      result.model = model
      if agent_pointer is not None and agent_pointer != '' and agent_pointer != 'None':
        result.agent_id_pointer = uuid.UUID(agent_pointer)
      session.commit()
      return {
        "Id": str(result.id),
        "Name": result.name,
        "Description": result.description,
        "Instructions": result.system_prompt,
        "Model": result.model,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in result.documents],
        "Director": result.director,
        "WrapperPrompt": result.wrapper_prompt,
        "InitialPrompt": result.initial_prompt,
        "AgentPointer": str(result.agent_id_pointer),
        "PromptChaining": result.prompt_chaining,
        "Created": result.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": result.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
      
  except Exception as e:
    print(f"An error occurred: {e}")
    return None
  
  
def get_director_agent_info(module_id: str):
  """
  Retrieves the details of the director agent.
  
  Parameters:
    module_id (str): The ID of the module the agent belongs to.
    
  Returns:
    dict or None: Director agent information or None if the operation fails.
  """
  try:
    with session_scope() as session:
      result = session.query(Agent).filter_by(module_id=module_id, director=True).first()
      if not result:
        logging.error(f"Failed to retrieve director agent for module {module_id}")
        return None
      
      return {
        "Id": str(result.id),
        "Name": result.name,
        "Description": result.description,
        "Instructions": result.system_prompt,
        "Model": result.model,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in result.documents],
        "Director": result.director,
        "WrapperPrompt": result.wrapper_prompt,
        "InitialPrompt": result.initial_prompt,
        "AgentPointer": str(result.agent_id_pointer),
        "PromptChaining": result.prompt_chaining,
        "Created": result.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": result.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
  
  except SQLAlchemyError as e:
    logging.error(f"An error occurred while retrieving director agent for module {module_id}: {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while retrieving director agent for module {module_id}: {e}")
    return None
      
def get_analytic_agent(module_id):
  """
  Retrieves the details of the analytic agent.
  
  Parameters:
    module_id (str): The ID of the module the agent belongs to.
  
  Returns:
    dict or None: Analytic agent info or None if the operation fails.
  """
  try:
    with session_scope() as session:
      result = session.query(Agent).filter_by(module_id=module_id, analytic=True).first()
      if not result:
        logging.error(f"Failed to retrieve analytic agent for module {module_id}")
        return None
      
      return {
        "Id": str(result.id),
        "Name": result.name,
        "Description": result.description,
        "Instructions": result.system_prompt,
        "Model": result.model,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in result.documents],
        "Director": result.director,
        "WrapperPrompt": result.wrapper_prompt,
        "InitialPrompt": result.initial_prompt,
        "AgentPointer": str(result.agent_id_pointer),
        "PromptChaining": result.prompt_chaining,
        "Created": result.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": result.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }

  except SQLAlchemyError as e:
    logging.error(f"An error occurred while retrieving analytic agent for module {module_id}: {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while retrieving analytic agent for module {module_id}: {e}")
    return None

def get_summarizer_agent(module_id):
  """
  Retrieves the details of the summarizer agent.
  
  Parameters:
    module_id (str): The ID of the module the agent belongs to.
  
  Returns:
    dict or None: Analytic agent info or None if the operation fails.
  """
  try:
    with session_scope() as session:
      result = session.query(Agent).filter_by(module_id=module_id, summarizer=True).first()
      if not result:
        logging.error(f"Failed to retrieve summarizer agent for module {module_id}")
        return None
      
      return {
        "Id": str(result.id),
        "Name": result.name,
        "Description": result.description,
        "Instructions": result.system_prompt,
        "Model": result.model,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in result.documents],
        "Director": result.director,
        "WrapperPrompt": result.wrapper_prompt,
        "InitialPrompt": result.initial_prompt,
        "AgentPointer": str(result.agent_id_pointer),
        "PromptChaining": result.prompt_chaining,
        "Created": result.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": result.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }

  except SQLAlchemyError as e:
    logging.error(f"An error occurred while retrieving summarizer agent for module {module_id}: {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while retrieving summarizer agent for module {module_id}: {e}")
    return None
  
      
def db_create_chat_session(thread_id: str, module_id: str, user_id: str):
  """
  Creates a new ChatSession in the database. Assigns the 'convo_analytics' and 'summaries' according to the
  current module settings. If a module is edited and doesn't have set summaries or analytics anymore, existing chatsessions
  remain set according to the module settings at the time of creation.
  
  Parameters:
    thread_id (str): The ID of the thread the conversation is held on.
    module_id (str): The ID of the module the conversation belongs to.
    user_id (str): The ID of the user that created the ChatSession.
    
  Returns:
    dict or None: The chat_session object or None if the operation fails.
  """
  try:
    with session_scope() as session:
      module = session.query(Module).filter(Module.id == module_id).first()
      chat_session = ChatSession(id=uuid.uuid4(),
                                 threadID=thread_id,
                                 moduleID=uuid.UUID(module_id),
                                 userID=uuid.UUID(user_id),
                                 convo_analytics=module.convo_analytics,
                                 summaries=module.summaries,
                                 module_name=module.name)
      session.add(chat_session)
      session.commit()
      return {
        'Id': str(chat_session.id),
        'ModuleID': str(chat_session.moduleID),
        'UserID': str(chat_session.userID),
        'LastAgent': str(chat_session.last_agent),
        'ThreadID': chat_session.threadID,
        'Created': chat_session.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': chat_session.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
  except SQLAlchemyError as e:
    logging.error(f"An error occurred while creating chat session for thread {thread_id}. {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while creating chat session for thread {thread_id}. {e}")
    return None
  
def retrieve_chat_sessions(user_id: str):
  """
  Retrieves all ChatSession rows tied to the `user_id`.
  
  Parameters:
    user_id (str): The ID of the user to whom the chat sessions belong to.
    
  Returns:
    list[dict] or None: A list with the ChatSession objects or None if the operation fails.
  """
  try:
    with session_scope() as session:
      chat_sessions = session.query(ChatSession).filter(ChatSession.userID == uuid.UUID(user_id)).all()
      return [{
        "Id": str(chat_session.id),
        'UserName': chat_session.user.email,
        'LastAgent': str(chat_session.last_agent),
        'ModuleName': chat_session.module_name,
        'ModuleID': str(chat_session.moduleID),
        'Analytics': chat_session.convo_analytics,
        'Summaries': chat_session.summaries,
        'Analysis': chat_session.analysis,
        'Summary': chat_session.summary,
        'MessagesLen': chat_session.messages_len,
        'ThreadID': chat_session.threadID,
        'Created': chat_session.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': chat_session.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for chat_session in chat_sessions]
  except SQLAlchemyError as e:
    logging.error(f"An SQLAlchemy error occurred while retrieving chat sessions for user {user_id}. {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while retrieving chat sessions for user {user_id}. {e}")
    return None
  
def delete_chat_session(chat_id: str):
  """
  Deletes a ChatSession from the database.
  
  Parameters:
    chat_id (str): The ID of the ChatSession to be removed.
    
  Returns:
    str or None: The ID of the deleted ChatSession or None if the operation fails.
  """
  try:
    with session_scope() as session:
      chat_session = session.query(ChatSession).filter(ChatSession.id == uuid.UUID(chat_id)).first()
      
      session.delete(chat_session)
      session.commit()
      return chat_id
  except SQLAlchemyError as e:
    logging.error(f"An error occurred while deleting chat session {chat_id}. {e}")
    return None
  except Exception as e:
    logging.error(f"An error occurred while deleting chat session {chat_id}. {e}")
    return None
  
  # def update_chat_session()... also add analysis, summary to chat session -> update on every safely_end_chat_session()

def update_chat_session(chat_session_id: str,
                        summary: str=None,
                        analysis: str=None,
                        last_agent: str=None,
                        messages_len: int=None):
  """
  Updates the `ChatSession` table with provided data.
  
  Parameters:
    chat_session_id (str): The ID of the ChatSession to be altered.
    summary (str): The summary of the ChatSession.
    analysis (str): The analysis of the ChatSession.
    last_agent (str): The ID of the last agent to interact with the ChatSession.
    messages_len (int): The current length of the chat session dialog.
  """
  try:
    with session_scope() as session:
      chat_session = session.query(ChatSession).filter(ChatSession.id == uuid.UUID(chat_session_id)).first()
      
      if summary is not None:
        chat_session.summary = summary
      if analysis is not None:
        chat_session.analysis = analysis
      if last_agent is not None:
        chat_session.last_agent = last_agent
      if messages_len is not None:
        chat_session.messages_len = messages_len
      session.commit()
      
      return {
        "Id": str(chat_session.id),
        'UserName': chat_session.user.email,
        'LastAgent': str(chat_session.last_agent),
        'ModuleName': chat_session.module_name,
        'ModuleID': str(chat_session.moduleID),
        'Analytics': chat_session.convo_analytics,
        'Summaries': chat_session.summaries,
        'Analysis': chat_session.analysis,
        'Summary': chat_session.summary,
        'MessagesLen': chat_session.messages_len,
        'ThreadID': chat_session.threadID,
        'Created': chat_session.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'LastModified': chat_session.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
  except Exception as e:
    logging.error(f"An error occurred while updating chat session {chat_session_id}. {e}")