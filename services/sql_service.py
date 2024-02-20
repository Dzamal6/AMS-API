from database.database import SessionLocal, session_scope
from database.models import User, Role, Assistant
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
import uuid
from flask import jsonify
from datetime import datetime


def add_user(username, password, roles, assistants):
  id = str(uuid.uuid4())

  try:
      with session_scope() as session:
          new_user = User(id=id,
                          username=username,
                          password=password,
                          roles=roles,
                          assistants=assistants)
          session.add(new_user)
          session.flush()  # Flush the session to ensure 'new_user' is persisted and can be queried

          # Directly use 'new_user' object, no need to re-query unless there's a specific reason
          roles = get_user_roles(new_user.roles)
          assistants = get_user_assistants(new_user.assistants)

          return jsonify({
              "message": "Registration successful",
              "response": {
                  "Id": id,  # No need to re-convert 'id' to string
                  "Created": new_user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                  "LastModified": new_user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                  "Username": new_user.username,
                  "Roles": roles,
                  "Assistants": assistants
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
  
      return jsonify({'message': 'User removed successfully'}), 200
  except NoResultFound:
    return jsonify({'message': 'User not found'}), 404
  except Exception as e:
    print(f"Error: {e}")
    return jsonify({'message': 'An error occurred'}), 500


def login_user(username, password):
  try:
    with session_scope() as session:
      user = session.query(User).filter(User.username == username,
                                        User.password == password).first()
  
      if user:
        user_data = {
            "Id":
            str(user.id),
            "Username":
            user.username,
            "Roles":
            get_user_roles([role.id for role in user.roles]),
            "Assistants":
            get_user_assistants([assistant.id for assistant in user.assistants]),
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


def check_user_exists(username):
  try:
    with session_scope() as session:
      result = session.query(User).filter_by(username=username).first()
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
          "Id": str(assistant.id),
          "Name": assistant.name,
          "Created": assistant.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
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
      user_query = session.query(User).all()
      users = [{
          "Id":
          str(user.id),
          "Username":
          user.username,
          "Roles":
          get_user_roles([role.id for role in user.roles]),
          "Assistants":
          get_user_assistants([assistant.id for assistant in user.assistants]),
          "Created":
          user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
          "LastModified":
          user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
      } for user in user_query]
      return users
  except Exception as e:
    print(f"An error occured: {e}")
    return []


def get_user(username):
  try:
    with session_scope() as session:
      user = session.query(User).filter(User.username == username).first()
  
      if user:
        user_data = {
            'id':
            str(user.id),
            'username':
            user.username,
            'roles':
            get_user_roles([role.id for role in user.roles]),
            'assistants':
            get_user_assistants([assistant.id for assistant in user.assistants]),
            'password_hash':
            user.password_hash,
            'created':
            user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            'last_modified':
            user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }
        # print(user_data)
        return user_data
        # return {'id': user_data['id'], 'username': user_data['username'],
        #        'roles': user_data['roles'], 'assistants': user_data['assistants'],
        #         'password': user_data['password_hash']}
      else:
        return {}
  except Exception as e:
    print(f"An error occured: {e}")
    return {}


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
      user = session.query(User).filter_by(id=user_id).first()
  
      if user:
        if username is not None:
          user.username = username
        if password is not None:
          user.password = password
        if roles is not None:
          user.roles = roles
        if assistants is not None:
          user.assistants = assistants
  
        session.commit()
  
        updated_user = {
            "Id": str(user.id),
            "Created": user.created.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "LastModified": user.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "Username": user.username,
            "Roles": user.roles,
            "Assistants": user.assistants
        }
  
        return updated_user
      else:
        print(f"User with ID {user_id} not found")
        return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None
