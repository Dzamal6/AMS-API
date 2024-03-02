from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool 
from config import POSTGRES_CONNECTION_STRING
from database.base import Base
from database.models import User, Role, Assistant, TokenUsage, Document
from functions import hash_password
import uuid
from contextlib import contextmanager
import os
import hashlib

engine = create_engine(POSTGRES_CONNECTION_STRING, echo=True, pool_size=4, max_overflow=0, pool_recycle=60)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.bind = engine


@contextmanager
def session_scope():
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
  try:
    with session_scope() as session:
      for filename in os.listdir('docs'):
        file_path = os.path.join('docs', filename)

        with open(file_path, 'rb') as file:
          file_content = file.read()

        file_hash = hashlib.sha256(file_content).hexdigest()

        if session.query(Document).filter_by(content_hash=file_hash).first():
          print(f"Duplicate found, skipping: {filename}")
          continue

        document = Document(id=uuid.uuid4(), file=file_content, content_hash=file_hash)
        session.add(document)
  except Exception as e:
    print(f"An error occured during document upload: {e}")
