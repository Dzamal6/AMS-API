from database.database import session_scope
from database.models import Agent, Module, User, Role, Document
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

def get_modules_as_dicts(modules):
  """
  Converts a list of module objects to a list of dictionaries containing module IDs and names.

  Parameters:
      modules (list): A list of module objects.

  Returns:
      list of dict: A list of dictionaries where each dictionary represents an module with `Id` and `Name` keys.
  """
  return [{"Id": str(module.id), "Name": module.name} for module in modules]

def compute_file_hash(doc):
    """ Compute SHA-256 hash for a file's content. """
    doc_content = doc.read()
    doc.seek(0)
    return hashlib.sha256(doc_content).hexdigest()

def check_for_duplicate(hashes, session):
    """ Check the database for existing documents with matching hashes. """
    existing_docs = session.query(Document).filter(Document.content_hash.in_(hashes)).all()
    return {doc.content_hash: doc for doc in existing_docs}

def associate_modules(existing_doc, module_ids, session):
    """ Associate new modules with an existing document if they are not already associated. """
    existing_module_ids = {str(module.id) for module in existing_doc.modules}
    new_module_ids = set(module_ids) - existing_module_ids
    
    if new_module_ids:
        print(f'Associating file {existing_doc.id} with modules {new_module_ids}. Existing module ids: {existing_module_ids}')
        new_modules = session.query(Module).filter(Module.id.in_(new_module_ids)).all()
        existing_doc.modules.extend(new_modules)
        session.commit()
        
def get_doc_content(doc):
    """ Retrieve contents of a document. """
    content = doc.read()
    doc.seek(0)
    return content

def create_director_agent(agent_details: dict[str, str | bool],
                          module_id: str, session):
    """
    Create a default director agent for directing conversations within a module.
    
    Parameters:
        agent_details (dict): A dictionary containing the agent's details. NOTE director param doesn't need to be passed since it is set to True by the method. Only 'name', 'model' and 'system_prompt' are necessary.
        module_id (str): The ID of the module to which the agent belongs.
        session (Session): A database session object.
    
    Returns:
        UUID: The Id of the created agent in the UUID format.
    """
    new_agent = Agent(id=uuid.uuid4(),
                        name=agent_details['name'],
                        system_prompt=agent_details['system_prompt'],
                        description=agent_details['description'],
                        model=agent_details['model'],
                        director=True,
                        module_id=uuid.UUID(module_id))
    module = session.query(Module).filter(
          Module.id == module_id).first()
    new_agent.module = module

    session.add(new_agent)
    session.commit()
    
    return new_agent.id