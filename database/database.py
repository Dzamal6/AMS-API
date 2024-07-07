from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool 
from config import POSTGRES_CONNECTION_STRING
from database.base import Base
from database.models import User, Role, Document
from util_functions.functions import hash_password
import uuid
from contextlib import contextmanager
import os
import hashlib
from werkzeug.utils import secure_filename

engine = create_engine(POSTGRES_CONNECTION_STRING, pool_size=4, max_overflow=0, pool_recycle=60) # set echp=True for elaborate logging
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.bind = engine


@contextmanager
def session_scope():
  """
  Provides a transactional scope for database operations using SQLAlchemy. Ensures that all database
  interactions within the scope are committed or rolled back appropriately.

  Yields:
      session (Session): A SQLAlchemy session object to handle database transactions.

  Raises:
      SQLAlchemyError: Handles SQL-related errors during transaction, like conflicts or connectivity issues.
      Exception: Captures and logs any unexpected exceptions, ensuring the session is rolled back and closed properly.

  Usage:
      with session_scope() as session:
          model_instance = Model(data=value)
          session.add(model_instance)
          # Other database operations follow

  This usage ensures that database operations are transactionally secure, with changes automatically
  committed on success or rolled back on failure.
  """
  session = SessionLocal()
  try:
    yield session
    session.commit()
  except SQLAlchemyError as e:
    session.rollback()
    print(f'Database error occured: {e}')
    raise
  except Exception as e:
    session.rollback()
    print(f'Unexpected error occured: {e}')
    raise
  finally:
    session.close()
      

def seed_data():
  """
  Seeds the database with essential roles and a default admin user to ensure the application
  functions correctly from the start.

  Details:
      - Creates roles: `Admin`, `User`, `Worker`, `Trainee`.
      - Adds a default admin user with username 'user1' and password 'pass123'.

  Note:
      - Should only be executed once during the initial setup of the application.
      - It's crucial for setting up initial access controls and user management capabilities.

  Usage:
      Called at the application's initial deployment to prepare the database for operation.
  """
  try:
    with session_scope() as session:
      if session.query(User).first() is None:
        admin_role = Role(id=uuid.uuid4(), name='Admin')
        master_role = Role(id=uuid.uuid4(), name='Master')
        worker_role = Role(id=uuid.uuid4(), name='Worker')
        trainee_role = Role(id=uuid.uuid4(), name='Trainee')
        hashed_password = hash_password('pass123')
        new_user = User(id=uuid.uuid4(),
                        username='user1',
                        password_hash=hashed_password,
                        roles=[admin_role, master_role])
        session.add_all(
            [admin_role, master_role, worker_role, trainee_role, new_user])
        session.commit()
  except Exception as e:
    print(f"An error occurred during seeding: {e}")

def upload_documents():
  """
  Uploads sample documents from a specified directory to the database. This method is
  optional and not required for the core functionality of the application.

  Note:
      - Requires a `docs` directory at the project root containing the sample files.
      - This method is not essential for the app's operations but may be used for demo or testing purposes.

  Usage:
      Typically called during the initial setup or for populating the database with sample data for demonstrations.
  """
  try:
      with session_scope() as session:
          docs_dir = 'docs'
          for filename in os.listdir(docs_dir):
              safe_name = secure_filename(filename)
              safe_name = safe_name.split('.')[0]
              file_path = os.path.join(docs_dir, filename)
              with open(file_path, 'rb') as file:
                  file_content = file.read()
              file_hash = hashlib.sha256(file_content).hexdigest()
              if session.query(Document).filter_by(content_hash=file_hash).first():
                  print(f"Duplicate found, skipping: {safe_name}")
                  continue
              document = Document(id=uuid.uuid4(), name=safe_name, content_hash=file_hash, file=file_content)
              session.add(document)
              print(f"Document uploaded: {safe_name}")

  except Exception as e:
      print(f"An error occurred during document upload: {e}")
