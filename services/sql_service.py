from database.database import SessionLocal, session_scope
from database.models import User, Role, Assistant, ChatSession
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
import uuid
from flask import jsonify
from datetime import datetime
from sql_functions import get_roles_as_dicts, get_assistants_as_dicts
from functions import hash_password


def get_user_chat_sessions(user_id: str, assistant_id: str):
  try:
    with session_scope() as session:
      query_sessions = session.query(ChatSession).filter(ChatSession.userID == uuid.UUID(user_id), ChatSession.assistantID == uuid.UUID(assistant_id)).all()
      return [{"Id": str(session.id), "User": session.userID, "Assistant": session.assistantID, 'Created': session.created.strftime("%Y-%m-%d %H:%M:%S"), 'LastModified': session.last_modified.strftime("%Y-%m-%d %H:%M:%S")} for session in query_sessions]
      
  except SQLAlchemyError as e:
    print(f'Database Error: {e}')
    return None
  except Exception as e:
    print(f'Error: {e}')
    return None

    
def create_chat_session(user_id: str, assistant_id: str):
  try:
    with session_scope() as session:
      chat_session = ChatSession(id=uuid.uuid4(), userID=user_id, assistantID=assistant_id)
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
        return {'Id': assistant.id, 'Name': assistant.name, 'Created': assistant.created, 'Token': assistant.token, 'ProjectId': assistant.projectID}
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
        assistants_uuids = [uuid.UUID(assistant_id) for assistant_id in assistants]
        new_user = User(id=id,
                          username=username,
                          password_hash=password,
                          roles=session.query(Role).filter(Role.id.in_(roles_uuids)).all(),
                          assistants = session.query(Assistant).filter(Assistant.id.in_(assistants_uuids)).all())

        session.add(new_user)
        session.commit()

        return jsonify({
              "message": "Registration successful",
              "response": {
                  "Id": id,
                  "Created": new_user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                  "LastModified": new_user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                  "Username": new_user.username,
                "Roles": get_roles_as_dicts(new_user.roles),
                "Assistants": get_assistants_as_dicts(new_user.assistants)
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
  
      return jsonify({'message': 'User removed successfully', 'user': {'id': user.id}}), 200
  except NoResultFound:
    return jsonify({'message': 'User not found'}), 404
  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500
    
# DEPRECATED
def login_user(username, password):
  try:
    with session_scope() as session:
      user = session.query(User).filter(User.username == username, User.password == password).first()
      if user:
        roles = [role.name for role in user.roles]
        assistants = [assistant.name for assistant in user.assistants]
        user_data = {
            "Id":
            str(user.id),
            "Username":
            user.username,
            "Roles":
            roles,
            "Assistants":
            assistants,
            "Created":
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified":
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }
        return {'user': user_data, 'status': 200}
      else:
        return {'message': "User not found", 'status': 404}
  except Exception as e:
    print(f"Error: {e}")
    return {'message': 'An error occurred', 'status': 500}


def check_user_exists(user_id):
  try:
    with session_scope() as session:
      result = session.query(User).filter_by(id=user_id).first()
      return result is not None
  except Exception as e:
    print(f"Error: {e}")
    return False

# WORKS
def get_all_roles():
  try:
    with session_scope() as session:
      roles_query = session.query(Role).all()
      roles = [{"Id": str(role.id), "Name": role.name} for role in roles_query]
      return roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []

# WORKS
def get_user_roles(user_roles_ids):
  try:
    with session_scope() as session:
      roles = session.query(Role).filter(Role.id.in_(user_roles_ids)).all()
      user_roles = [{"Id": str(role.id), "Name": role.name} for role in roles]
      return user_roles
  except Exception as e:
    print(f"An error occured: {e}")
    return []

# WORKS
def get_all_assistants():
  try:
    with session_scope() as session:
      assistants_query = session.query(Assistant).all()
      assistants = [{
          "Id": str(assistant.id),
          "Name": assistant.name,
          "Created": assistant.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
      } for assistant in assistants_query]
      return assistants
  except Exception as e:
    print(f"An error occured: {e}")
    return []

# WORKS
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
      assistants_dict = {assistant.id: assistant for assistant in all_assistants}

      users_data = []
      for user in users:
        user_roles_ids = [role.id for role in user.roles]
        user_assistants_ids = [assistant.id for assistant in user.assistants]

        user_roles = [{"Id": str(role.id), "Name": role.name} for role_id in user_roles_ids for role in (roles_dict.get(role_id),) if role]
        user_assistants = [{"Id": str(assistant.id), "Name": assistant.name} for assistant_id in user_assistants_ids for assistant in (assistants_dict.get(assistant_id),) if assistant]

        users_data.append({
          "Id": str(user.id),
          "Username": user.username,
          "Roles": user_roles,
          "Assistants": user_assistants,
          "Created": user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
          "LastModified": user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        })
      return users_data
  except Exception as e:
    print(f"An error occured: {e}")
    return []
    
# WORKS
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
            get_user_assistants([assistant.id for assistant in user.assistants]),
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

# WORKS
def add_assistant(project_token, project_name, project_vID, project_id):
  try:
    with session_scope() as session:
      existing_assistant = session.query(Assistant).filter(Assistant.name == project_name).first()

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
        'Created': new_assistant.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
      }
      
      return jsonify({'message': 'Assistant added to the database.', 'data': assistant_data}), 200

  except Exception as e:
      print(f"An error occurred: {e}")
      return jsonify({'error': "An error occurred while adding the assistant."}), 400

# WORKS
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
          user.roles = session.query(Role).filter(Role.id.in_(roles_uuids)).all()
        if assistants is not None:
          assistants_uuids = [uuid.UUID(assistant_id) for assistant_id in assistants]
          user.assistants = session.query(Assistant).filter(Assistant.id.in_(assistants_uuids)).all()

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
