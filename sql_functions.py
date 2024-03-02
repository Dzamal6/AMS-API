from database.database import session_scope
from database.models import User, Role, Assistant


def get_roles_as_dicts(roles):
  return [{"Id": str(role.id), "Name": role.name} for role in roles]

def get_assistants_as_dicts(assistants):
  return [{"Id": str(assistant.id), "Name": assistant.name} for assistant in assistants]
