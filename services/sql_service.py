from database.database import SessionLocal, session_scope
from database.models import User, Role, Assistant, ChatSession, Transcript, Document, Agent
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
import uuid
from flask import jsonify
from datetime import datetime
from sql_functions import get_roles_as_dicts, get_assistants_as_dicts
from functions import hash_password
from werkzeug.utils import secure_filename
import os
import hashlib
import io
from typing import cast


def get_all_transcripts():
  try:
    with session_scope() as session:
      transcripts = session.query(Transcript).all()

      if not transcripts:
        print('No transcripts found')
        return None

      return [{
          'Id':
          str(transcript.id),
          'TranscriptID':
          str(transcript.transcriptID),
          'SessionID':
          str(transcript.sessionID),
          'UserID':
          str(transcript.userID),
          'Username':
          str(transcript.username),
          "LastModified":
          transcript.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
          'Created':
          transcript.created.strftime("%Y-%m-%d %H:%M:%S")
      } for transcript in transcripts]

  except SQLAlchemyError as e:
    print(f"Database Error: {e}")
    return None

  except Exception as e:
    print(f"Error: {e}")
    return None


def create_transcript(transcript_id: str, session_id: str, user_id: str,
                      username: str):
  try:
    with session_scope() as session:
      transcript = Transcript(id=uuid.uuid4(),
                              userID=uuid.UUID(user_id),
                              sessionID=uuid.UUID(session_id),
                              transcriptID=transcript_id,
                              username=username)

      session.add(transcript)
      session.commit()

      return {'Id': str(transcript.id)}

  except SQLAlchemyError as e:
    print(f"Database Error: {e}")
    return None

  except Exception as e:
    print(f"Error: {e}")
    return None


def get_all_chat_sessions():
  try:
    with session_scope() as session:
      chat_sessions_query = session.query(ChatSession).all()
      if not chat_sessions_query:
        print('No chat sessions found.')
        return None

      return [{
          "Id":
          str(chat_session.id),
          "UserID":
          str(chat_session.userID),
          "AssistantID":
          str(chat_session.id),
          "Created":
          str(chat_session.created.strftime("%Y-%m-%d %H:%M:%S")),
          "LastModified":
          str(chat_session.last_modified.strftime("%Y-%m-%d %H:%M:%S"))
      } for chat_session in chat_sessions_query]

  except SQLAlchemyError as e:
    print(f'Database Error: {e}')
    return None
  except Exception as e:
    print(f'Error: {e}')
    return None


def remove_chat_session(sessionID: str):
  try:
    uuid.UUID(sessionID)
  except ValueError:
    print(f'Invalid session ID: {sessionID}.')
    return sessionID

  try:
    with session_scope() as session:
      chat_session = session.query(ChatSession).filter(
          ChatSession.id == sessionID)

      if not chat_session:
        print(f'Database Error 404: Chat session {sessionID} not found.')
        return None

      chat_session.delete()
      session.commit()
      print(f'Chat session {sessionID} deleted.')
      return sessionID

  except SQLAlchemyError as e:
    print(f'Database Error: {e}')
    return None
  except Exception as e:
    print(f'Error: {e}')
    return None


def get_user_chat_sessions(user_id: str, assistant_id: str):
  try:
    with session_scope() as session:
      query_sessions = session.query(ChatSession).filter(
          ChatSession.userID == uuid.UUID(user_id),
          ChatSession.assistantID == uuid.UUID(assistant_id)).all()
      return [{
          "Id":
          str(session.id),
          "User":
          session.userID,
          "Assistant":
          session.assistantID,
          'Created':
          session.created.strftime("%Y-%m-%d %H:%M:%S"),
          'LastModified':
          session.last_modified.strftime("%Y-%m-%d %H:%M:%S")
      } for session in query_sessions]

  except SQLAlchemyError as e:
    print(f'Database Error: {e}')
    return None
  except Exception as e:
    print(f'Error: {e}')
    return None


def create_chat_session(user_id: str, assistant_id: str):
  try:
    with session_scope() as session:
      chat_session = ChatSession(id=uuid.uuid4(),
                                 userID=user_id,
                                 assistantID=assistant_id)
      session.add(chat_session)
      session.commit()

      return {'Id': str(chat_session.id)}

  except SQLAlchemyError as e:
    print(f"Database Error: {e}")
    return None

  except Exception as e:
    print(f"Error: {e}")
    return None


def get_assistant_by_id(assistant_id):
  try:
    with session_scope() as session:
      assistant = session.query(Assistant).filter_by(id=assistant_id).first()
      if assistant:
        return {
            'Id': assistant.id,
            'Name': assistant.name,
            'Created': assistant.created,
            'Token': assistant.token,
            'ProjectId': assistant.projectID,
            'VersionId': assistant.vID,
        }
      else:
        return None

  except SQLAlchemyError as e:
    print(f"Database Error: {e}")
    return jsonify({'message': "Assistant could not be resolved."}), 400

  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500


def add_user(username, password, roles, assistants):
  id = str(uuid.uuid4())

  try:
    with session_scope() as session:
      roles_uuids = [uuid.UUID(role_id) for role_id in roles]
      assistants_uuids = [
          uuid.UUID(assistant_id) for assistant_id in assistants
      ]
      new_user = User(id=id,
                      username=username,
                      password_hash=password,
                      roles=session.query(Role).filter(
                          Role.id.in_(roles_uuids)).all(),
                      assistants=session.query(Assistant).filter(
                          Assistant.id.in_(assistants_uuids)).all())

      session.add(new_user)
      session.commit()

      return jsonify({
          "message": "Registration successful",
          "response": {
              "Id":
              id,
              "Created":
              new_user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
              "LastModified":
              new_user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
              "Username":
              new_user.username,
              "Roles":
              get_roles_as_dicts(new_user.roles),
              "Assistants":
              get_assistants_as_dicts(new_user.assistants)
          }
      }), 200

  except SQLAlchemyError as e:
    print(f"Error: {e}")
    return jsonify({'message': "Registration failed"}), 400


def remove_user(user_id):
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


def check_user_exists(user_id):
  try:
    with session_scope() as session:
      result = session.query(User).filter_by(id=user_id).first()
      return result is not None
  except Exception as e:
    print(f"Error: {e}")
    return False


def get_all_roles():
  try:
    with session_scope() as session:
      roles_query = session.query(Role).all()
      roles = [{"Id": str(role.id), "Name": role.name} for role in roles_query]
      return roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user_roles(user_roles_ids):
  try:
    with session_scope() as session:
      roles = session.query(Role).filter(Role.id.in_(user_roles_ids)).all()
      user_roles = [{"Id": str(role.id), "Name": role.name} for role in roles]
      return user_roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_all_assistants():
  try:
    with session_scope() as session:
      assistants_query = session.query(Assistant).all()
      assistants = [{
          "Id":
          str(assistant.id),
          "Name":
          assistant.name,
          "Created":
          assistant.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for assistant in assistants_query]
      return assistants
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user_assistants(user_assistants_ids):
  try:
    with session_scope() as session:
      assistants = session.query(Assistant).filter(
          Assistant.id.in_(user_assistants_ids)).all()
      user_assistants = [{
          "Id": str(assistant.id),
          "Name": assistant.name
      } for assistant in assistants]
      return user_assistants
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_all_users():
  try:
    with session_scope() as session:
      users = session.query(User).all()

      all_roles = session.query(Role).all()
      all_assistants = session.query(Assistant).all()

      roles_dict = {role.id: role for role in all_roles}
      assistants_dict = {
          assistant.id: assistant
          for assistant in all_assistants
      }

      users_data = []
      for user in users:
        user_roles_ids = [role.id for role in user.roles]
        user_assistants_ids = [assistant.id for assistant in user.assistants]

        user_roles = [{
            "Id": str(role.id),
            "Name": role.name
        } for role_id in user_roles_ids for role in (roles_dict.get(role_id), )
                      if role]
        user_assistants = [
            {
                "Id": str(assistant.id),
                "Name": assistant.name
            } for assistant_id in user_assistants_ids
            for assistant in (assistants_dict.get(assistant_id), ) if assistant
        ]

        users_data.append({
            "Id":
            str(user.id),
            "Username":
            user.username,
            "Roles":
            user_roles,
            "Assistants":
            user_assistants,
            "Created":
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified":
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        })
      return users_data
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user(username):
  try:
    with session_scope() as session:
      user = session.query(User).filter(User.username == username).first()

      if user:
        user_data = {
            'Id':
            str(user.id),
            'Username':
            user.username,
            'Roles':
            get_user_roles([role.id for role in user.roles]),
            'Assistants':
            get_user_assistants(
                [assistant.id for assistant in user.assistants]),
            'password_hash':
            user.password_hash,
            'Created':
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            'LastModified':
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }

        return user_data
      else:
        return {}
  except Exception as e:
    print(f"An error occured: {e}")
    return {}


def add_assistant(project_token, project_name, project_vID, project_id):
  try:
    with session_scope() as session:
      existing_assistant = session.query(Assistant).filter(
          Assistant.name == project_name).first()

      if existing_assistant:
        print(f"Assistant {project_name} already exists.")
        return jsonify({'error': 'Assistant already exists.'}), 400

      id = uuid.uuid4()
      new_assistant = Assistant(id=id,
                                name=project_name,
                                token=project_token,
                                vID=project_vID,
                                projectID=project_id)
      session.add(new_assistant)
      session.commit()

      assistant_data = {
          'Id': str(new_assistant.id),
          'Name': new_assistant.name,
          'Created':
          new_assistant.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
      }

      return jsonify({
          'message': 'Assistant added to the database.',
          'data': assistant_data
      }), 200

  except Exception as e:
    print(f"An error occurred: {e}")
    return jsonify({'error':
                    "An error occurred while adding the assistant."}), 400


def delete_assistant(project_name):
  try:
    with session_scope() as session:
      result = session.query(Assistant).filter_by(name=project_name).first()

      if result:
        session.delete(result)
        session.commit()
        print(f"Deleted assistant {project_name}")
        return True
      else:
        print(f"Assistant {project_name} not found")
        return False
  except Exception as e:
    print(f"An error occurred: {e}")
    return False


def update_user(user_id,
                username=None,
                password=None,
                roles=None,
                assistants=None):

  try:
    with session_scope() as session:
      user = session.query(User).filter(User.id == user_id).first()

      if user:
        if username is not None:
          user.username = username
        if password is not None:
          user.password_hash = password
        if roles is not None:
          roles_uuids = [uuid.UUID(role_id) for role_id in roles]
          user.roles = session.query(Role).filter(
              Role.id.in_(roles_uuids)).all()
        if assistants is not None:
          assistants_uuids = [
              uuid.UUID(assistant_id) for assistant_id in assistants
          ]
          user.assistants = session.query(Assistant).filter(
              Assistant.id.in_(assistants_uuids)).all()

        current_time = datetime.now()
        session.commit()

        updated_user = {
            "Id": str(user.id),
            "Created": user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified": current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "Username": user.username,
            "Roles": get_roles_as_dicts(user.roles),
            "Assistants": get_assistants_as_dicts(user.assistants)
        }

        return updated_user
      else:
        print(f"User with ID {user_id} not found")
        return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

# TODO: files already included in the db need to be able to receive new agent relationships
def upload_files(files):
  responses = []
  files_with_ids = {
    str(uuid.uuid4()): file
    for file in files
  }
  try:
    with session_scope() as session:
      file_data = []
      for file_id, doc in files_with_ids.items():
        doc_content = doc.read()
        doc.seek(0)
        doc_hash = hashlib.sha256(doc_content).hexdigest()
        file_data.append((doc, file_id, doc.filename, doc_hash, doc_content))

      hashes = [f[3] for f in file_data]
      existing_docs = session.query(Document).filter(
          Document.content_hash.in_(hashes)).all()
      existing_hashes = {doc.content_hash: doc for doc in existing_docs}

      for doc, file_id, filename, doc_hash, doc_content in file_data:
        if doc_hash in existing_hashes:
            existing_doc = existing_hashes[doc_hash]
            print(f"Duplicate found, including existing file in response: {existing_doc.id}")
            responses.append(('success', {
                'message': f'Duplicate document found for file {file_id}, including existing file.',
                "Id": existing_doc.id,
                "Name": existing_doc.name,
                "Content_hash": existing_doc.content_hash,
                "Created": existing_doc.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                "LastModified": existing_doc.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            }))
            continue

        document = Document(id=file_id, 
                            name=filename, 
                            content_hash=doc_hash, 
                            content=doc_content)
        session.add(document)
        session.commit()

        responses.append(('success', {
            "Id":
            document.id,
            "Name":
            document.name,
            "Content_hash":
            document.content_hash,
            "Created":
            document.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified":
            document.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }))

  except Exception as e:
    print(f"An error occurred: {e}")
    responses.append(('error', {
        'error': f'An error occurred during upload. {str(e)}'
    }))

  return responses


def get_all_files():
  try:
    with session_scope() as session:
      docs = session.query(Document).all()
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


def delete_doc(docId):
  try:
    with session_scope() as session:
      result = session.query(Document).filter_by(id=docId).first()
      if result:
        session.delete(result)
        session.commit()
        print(f"Deleted document with ID {docId}")
        return docId
      else:
        print(f"Document with ID {docId} not found")
        return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def get_file(docId):
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
  try:
    with session_scope() as session:
      agent = session.query(Agent).filter_by(id=agentId).first()
      if not agent:
        return None

      blobs = []
      for file in agent.documents:
        content_bytes = cast(bytes, file.content)
        blobs.append(io.BytesIO(content_bytes))

      agent_dict = {
        "Id": agent.id,
        "Name": agent.name,
        "Instructions": agent.system_prompt,
        "Model": agent.model,
        "Documents_IO": blobs,
        "Created": agent.created,
        "LastModified": agent.last_modified,
      }

      return agent_dict
  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def upload_agent_metadata(agent_details: dict[str, str],
                          assistant_ids: list[str], document_ids: list[str]):
  try:
    with session_scope() as session:
      new_agent = Agent(id=uuid.uuid4(),
                        name=agent_details['name'],
                        system_prompt=agent_details['system_prompt'],
                        description=agent_details['description'],
                        model=agent_details['model'])
      assistants = session.query(Assistant).filter(
          Assistant.id.in_(assistant_ids)).all()
      new_agent.assistants = assistants

      if document_ids is not []:
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
          "Description": new_agent.description,
          "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in new_agent.documents],
          "Created": new_agent.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
          "LastModified": new_agent.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }

  except Exception as e:
    print(f"An error occurred: {e}")
    return None


def retrieve_all_agents():
  try:
    with session_scope() as session:
      agents = session.query(Agent).all()

      return [{
        "Id": agent.id,
        "Name": agent.name,
        "Model": agent.model,
        "Instructions": agent.system_prompt,
        "Description": agent.description,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in agent.documents],
        "Created": agent.created,
        "LastModified": agent.last_modified
      } for agent in agents]

  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def delete_agent(agent_id):
  try:
    with session_scope() as session:
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

def update_agent(agent_id, name, description, instructions, model, document_ids):
  try:
    with session_scope() as session:
      result = session.query(Agent).filter_by(id=agent_id).first()
      if not result:
        return None

      if document_ids is not []:
        documents = session.query(Document).filter(
            Document.id.in_(document_ids)).all()
        result.documents = documents

      result.name = name
      result.description = description
      result.system_prompt = instructions
      result.model = model
      session.commit()
      return {
        "Id": str(result.id),
        "Name": result.name,
        "Description": result.description,
        "Instructions": result.system_prompt,
        "Model": result.model,
        "Documents": [{"Id": str(doc.id), "Name": doc.name} for doc in result.documents],
        "Created": result.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "LastModified": result.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      }
      
  except Exception as e:
    print(f"An error occurred: {e}")
    return None