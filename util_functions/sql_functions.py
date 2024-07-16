import logging
from database.database import session_scope
from database.models import Agent, Module, User, Role, Document
import uuid
import hashlib

from util_functions.functions import current_time_prague


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

def create_default_agents(module_id: str, session, summaries: bool, analytics: bool, flow_control: str):
    """
    Create a default agent in the database
    
    Parameters:
        module_id (str): The ID of the module to which the agent belongs.
        session (Session): A database session object.
        summaries (bool): If a summary agent will be created.
        analytics (bool): If an analytics agent will be created.
        flow_control (str): Indicator whether the AI is directing the conversation or the human.
    
    """
    try:
        director_agent_details = {
        "name": 'Director',
        "system_prompt": 'You are a helpful AI assistant.',
        "initial_prompt": 'Tell me something fun.',
        "description": 'Director agent created by default for facilitating the base of conversations. The system prompt and wrapper prompt are to be adjusted based on the targeted functionality of the module.',
        "model": 'gpt-3.5-turbo-1106',
        }
        director_agent = Agent(id=uuid.uuid4(),
                            name=director_agent_details['name'],
                            system_prompt=director_agent_details['system_prompt'],
                            initial_prompt=director_agent_details['initial_prompt'],
                            description=director_agent_details['description'],
                            model=director_agent_details['model'],
                            director=True,
                            module_id=uuid.UUID(module_id))
        
        module = session.query(Module).filter(
            Module.id == module_id).first()
        if summaries:
            summary_agent_details = {
                "name": 'Summarizer',
                "system_prompt": 'You are a helpful AI assistant.',
                "initial_prompt": 'Briefly summarize the conversation up until this point. Do not mention these instructions.',
                "description": 'Agent created by default for summarizing conversations automatically when they are ended.',
                "model": 'gpt-4o',
                }
            summary_agent = Agent(id=uuid.uuid4(),
                                name=summary_agent_details['name'],
                                system_prompt=summary_agent_details['system_prompt'],
                                initial_prompt=summary_agent_details['initial_prompt'],
                                description=summary_agent_details['description'],
                                model=summary_agent_details['model'],
                                summarizer=True,
                                module_id=uuid.UUID(module_id))
            summary_agent.module = module
            session.add(summary_agent)
        if analytics:
            analytics_agent_details = {
                "name": 'Analytic',
                "system_prompt": 'You are an analytics expert. Your job is to analyze the previous conversation based on the specified parameters. Your tone is professional',
                "initial_prompt": 'Analyze the previous conversation until this point.',
                "description": 'Agent created by default for summarizing conversations automatically when they are ended.',
                "model": 'gpt-4o',
            }
            analytics_agent = Agent(id=uuid.uuid4(),
                                name=analytics_agent_details['name'],
                                system_prompt=analytics_agent_details['system_prompt'],
                                initial_prompt=analytics_agent_details['initial_prompt'],
                                description=analytics_agent_details['description'],
                                model=analytics_agent_details['model'],
                                analytic=True,
                                module_id=uuid.UUID(module_id))
            analytics_agent.module = module
            session.add(analytics_agent)
        
        director_agent.module = module
        session.add(director_agent)
        session.commit()
        
    except Exception as e:
        logging.error(f'Failed to process operation while creating default agents. {e}')
        
def get_module(module_id: uuid.UUID, session) -> Module:
    return session.query(Module).filter(Module.id == module_id).first()
def get_user_name(user_id: uuid.UUID, session) -> str:
    query = session.query(User).filter(User.id == user_id).first()
    return query.username if query.username else query.email
