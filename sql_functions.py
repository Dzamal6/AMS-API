from database.database import session_scope
from database.models import User, Role, Assistant


def get_roles_as_dicts(roles):
  """
  Converts a list of role objects to a list of dictionaries containing role IDs and names.

  Parameters:
      roles (list): A list of role objects.

  Returns:
      list of dict: A list of dictionaries where each dictionary represents a role with `Id` and `Name` keys.
  """
  return [{"Id": str(role.id), "Name": role.name} for role in roles]

def get_assistants_as_dicts(assistants):
  """
  Converts a list of assistant objects to a list of dictionaries containing assistant IDs and names.

  Parameters:
      assistants (list): A list of assistant objects.

  Returns:
      list of dict: A list of dictionaries where each dictionary represents an assistant with `Id` and `Name` keys.
  """
  return [{"Id": str(assistant.id), "Name": assistant.name} for assistant in assistants]
