import os
from pyairtable import Api
from pyairtable.formulas import match
import uuid
from flask import jsonify
from functions import check_admin, hash_password
from functions import get_user_info

api = Api(os.environ['AIRTABLE_API_KEY'])
user_table = api.table('appS1lC4Fzpmre5cF', 'tblTQJkH9Q6X77egQ')
roles_table = api.table('appS1lC4Fzpmre5cF', 'tblDUIO7Xh4MlHH5o')
assistants_table = api.table('appS1lC4Fzpmre5cF', 'tblIPljgf7aFSSpa6')


def add_user(username, password, roles, assistants):
  id = str(uuid.uuid4())
  user_table.create({
      'Id': id,
      'Username': username,
      'Password': password,
      'Roles': roles,
      'Assistants': assistants
  })
  res = user_table.first(formula=match({'Username': username, 'Id': id}))
  if res:
    roles = get_user_roles(res['fields']['Roles'])
    assistants = get_user_assistants(res['fields']['Assistants'])
    return jsonify({
        "message": "Registration successful",
        'response': {
            'Id': res['id'],
            'Created': res['fields']['Created'],
            'LastModified': res['fields']['LastModified'],
            'Roles': roles,
            'Assistants': assistants,
            'Username': res['fields']['Username']
        }
    }), 200
  else:
    return jsonify({'message': 'Registration failed'}), 400


def remove_user(id):
  res = user_table.delete(id)
  if res:
    return jsonify({"message": "User removed successfully", 'user': res}), 200
  else:
    return jsonify({'error': 'User not found'}), 404


def login_user(username, password):
  formula = match({'Username': username, 'Password': password})
  result = user_table.first(formula=formula)
  if result:
    return {'user': result, 'status': 200}
  else:
    return {'status': 401}


def check_user_exists(username):
  formula = match({'Username': username})
  result = user_table.first(formula=formula)
  return result


def get_all_roles():
  roles_response = roles_table.all()
  roles = []
  for record in roles_response:
    if 'fields' in record and 'Role' in record['fields']:
      role_id = record['id']
      role_name = record['fields']['Role']
      roles.append({'Id': role_id, 'Name': role_name})
    else:
      print("Role name not found in record's fields")
  return roles


def get_user_roles(user_roles_ids):
  roles = get_all_roles()
  user_roles = []
  for role_id in user_roles_ids:
    for role in roles:
      if role['Id'] == role_id:
        user_roles.append({'Id': role['Id'], 'Name': role['Name']})
        break

  return user_roles


def get_all_assistants():
  assistants_response = assistants_table.all()
  assistants = []
  for record in assistants_response:
    if 'fields' in record and 'name' in record['fields']:
      assistant_id = record['id']
      assistant_name = record['fields']['name']
      assistants.append({
          'Id': assistant_id,
          'Name': assistant_name,
          'Created': record['fields']['Created']
      })
    else:
      print("Assistant name not found in record's fields")
  return assistants


def get_user_assistants(user_assistants_ids):
  assistants = get_all_assistants()
  user_assistants = []
  for assistant_id in user_assistants_ids:
    for assistant in assistants:
      if assistant['Id'] == assistant_id:
        user_assistants.append({
            'Id': assistant['Id'],
            'Name': assistant['Name']
        })
        break

  return user_assistants


def get_all_users():
  users_response = user_table.all(fields=('Username', 'Roles', 'Assistants',
                                          'Created', 'LastModified'))
  users = []
  for record in users_response:
    if 'fields' in record:
      user_info = record['fields']
      user_info['Id'] = record['id']
      user_roles_ids = user_info.get('Roles', [])
      user_roles = get_user_roles(user_roles_ids)
      user_info['Roles'] = user_roles
      user_assistants_ids = user_info.get('Assistants', [])
      user_assistants = get_user_assistants(user_assistants_ids)
      user_info['Assistants'] = user_assistants
      users.append(user_info)

  return users


def get_user(username):
  formula = match({'Username': username})
  result = user_table.first(formula=formula)
  if result:
    return {'id': result['id'], 'fields': result['fields']}


def add_assistant(project_token, project_name, project_vID, project_id):
  formula = match({'name': project_name})
  result = assistants_table.first(formula=formula)
  if result:
    assistants_table.update(
        result['id'], {
            'vID': project_vID,
            'token': project_token,
            'name': project_name,
            'projectId': project_id
        })
    print(f"Assistant {project_name} updated")
    return result['id']
  else:
    assistants_table.create({
        'name': project_name,
        'token': project_token,
        'vID': project_vID,
        'projectId': project_id
    })
    print(f'Assistant {project_name} added')
    res = assistants_table.first(formula=formula)
    if res:
      return res['id']
    return None


def delete_assistant(project_name):
  formula = match({'name': project_name})
  result = assistants_table.first(formula=formula)
  if result:
    assistants_table.delete(result['id'])
    print(f'Deleted assistant "{project_name}"')
    return True
  else:
    print(f'Assistant "{project_name}" not found')
  return False


def update_user(user_id,
                username=None,
                password=None,
                roles=None,
                assistants=None):
  fields = {
      k: v
      for k, v in [('Username',
                    username), ('Password',
                                password), ('Roles',
                                            roles), ('Assistants', assistants)]
      if v
  }
  result = user_table.update(user_id, fields=fields)
  formula = match({'Id': result['id']})
  res = user_table.get(result['id'])
  if res:
    return {
        'Id': res['id'],
        'Created': res['fields']['Created'],
        'LastModified': res['fields']['LastModified'],
        'Username': res['fields']['Username'],
        'Roles': get_user_roles(res['fields']['Roles']),
        'Assistants': get_user_assistants(res['fields']['Assistants'])
    }


# def update_assistant_tokens(assistant_name, inp_tok, inp_cost, out_tok,
#                           out_cost):
#   records = token_table.all()
#   for record in records:
#     if 'Assistant' in record['fields'] and record['fields'][
#         'Assistant'] == assistant_name and 'Date' in record[
#             'fields'] and record['fields']['Date'] == str(current_date):
#       token_table.update(
#           record['id'], {
#               'Input Tokens': record['fields']['Input Tokens'] + inp_tok,
#               'Output Tokens': record['fields']['Output Tokens'] + out_tok,
#               'Input Cost': record['fields']['Input Cost'] + inp_cost,
#               'Output Cost': record['fields']['Output Cost'] + out_cost
#           })
#       print(record['id'])
#       return
#   token_table.create({
#       "Assistant": assistant_name,
#       'Input Tokens': inp_tok,
#       'Output Tokens': out_tok,
#       'Input Cost': inp_cost,
#       'Output Cost': out_cost,
#       "Date": str(current_date)
#   })
