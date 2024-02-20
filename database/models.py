from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from database.base import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
  __tablename__ = 'users'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  username = Column(String, unique=True, index=True)
  password_hash = Column(String(128))
  roles = relationship('Role', secondary='user_roles', back_populates='users')
  assistants = relationship('Assistant', secondary='user_assistants', back_populates='users')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Role(Base):
  __tablename__ = 'roles'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  users = relationship('User', secondary='user_roles', back_populates='roles')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Assistant(Base):
  __tablename__ = 'assistants'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  users = relationship('User', secondary='user_assistants', back_populates='assistants')
  token = Column(String, unique=True, index=True)
  vID = Column(String, unique=True, index=True)
  projectID = Column(String, unique=True, index=True)
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TokenUsage(Base):
  __tablename__ = 'token_usage'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  assistant = relationship('Assistant', secondary='assistant_usage')
  input_tokens = Column(Integer)
  output_tokens = Column(Integer)
  input_cost = Column(Integer)
  output_cost = Column(Integer)
  date = Column(DateTime, default=datetime.utcnow)

assistant_usage = Table('assistant_usage', Base.metadata,
    Column('assistant_id', UUID(as_uuid=True), ForeignKey('assistants.id'), primary_key=True),
    Column('token_usage_id', UUID(as_uuid=True), ForeignKey('token_usage.id'), primary_key=True)
)

user_roles = Table('user_roles', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)

user_assistants = Table('user_assistants', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('assistant_id', UUID(as_uuid=True), ForeignKey('assistants.id'), primary_key=True)
)