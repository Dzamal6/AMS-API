from database.database import session_scope
from database.models import User, Role, Assistant, Document
import uuid
import hashlib


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

def compute_file_hash(doc):
    """ Compute SHA-256 hash for a file's content. """
    doc_content = doc.read()
    doc.seek(0)
    return hashlib.sha256(doc_content).hexdigest()

def check_for_duplicate(hashes, session):
    """ Check the database for existing documents with matching hashes. """
    existing_docs = session.query(Document).filter(Document.content_hash.in_(hashes)).all()
    return {doc.content_hash: doc for doc in existing_docs}

def associate_assistants(existing_doc, assistant_ids, session):
    """ Associate new assistants with an existing document if they are not already associated. """
    existing_assistant_ids = {assistant.id for assistant in existing_doc.assistants}
    new_assistant_ids = set(assistant_ids) - existing_assistant_ids
    if new_assistant_ids:
        new_assistants = session.query(Assistant).filter(Assistant.id.in_(new_assistant_ids)).all()
        existing_doc.assistants.extend(new_assistants)
        session.commit()