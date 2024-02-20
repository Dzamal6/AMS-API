from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session
from config import POSTGRES_CONNECTION_STRING
from database.base import Base
from database.models import User, Role, Assistant, TokenUsage
from functions import hash_password
import uuid
from contextlib import contextmanager

engine = create_engine(POSTGRES_CONNECTION_STRING, pool_size=5, max_overflow=0)
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
