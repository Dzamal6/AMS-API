from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, LargeBinary
from sqlalchemy.orm import relationship, backref
from database.base import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

# MIGRATING CMDS: alembic revision --autogenerate -m "desc"
# MIGRATING CMDS: alembic upgrade head

class User(Base):
  __tablename__ = 'users'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  username = Column(String(30), unique=True, index=True)
  password_hash = Column(String(255), nullable=False)
  roles = relationship('Role', secondary='user_roles', back_populates='users')
  assistants = relationship('Assistant', secondary='user_assistants', back_populates='users')
  transcripts = relationship('Transcript', backref='user', lazy='dynamic', cascade='all, delete-orphan')
  chat_sessions = relationship('ChatSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Role(Base):
  __tablename__ = 'roles'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  users = relationship('User', secondary='user_roles', back_populates='roles')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  documents = relationship('Document', secondary='document_roles', back_populates='roles')

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
  assistantID = Column(UUID(as_uuid=True), ForeignKey('assistants.id', ondelete='CASCADE'))
  assistant = relationship('Assistant', backref=backref('token_usages', cascade='all, delete-orphan'))
  input_tokens = Column(Integer)
  output_tokens = Column(Integer)
  input_cost = Column(Integer)
  output_cost = Column(Integer)
  date = Column(DateTime, default=datetime.utcnow)

# Probably redundant
class Transcript(Base):
  __tablename__ = 'transcripts'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  transcriptID = Column(String, unique=True, index=True)
  sessionID = Column('ChatSession', ForeignKey('chat_sessions.id'), nullable=False)
  userID = Column('User', ForeignKey('users.id'), nullable=False)
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatSession(Base):
  __tablename__ = 'chat_sessions'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  userID = Column('User', ForeignKey('users.id'), nullable=False)
  assistantID = Column('Assistant', ForeignKey('assistants.id'), nullable=False)
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
  __tablename__ = "documents"
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  file = Column(LargeBinary)
  content_hash = Column(String(64), unique=True)
  roles = relationship('Role', secondary='document_roles', back_populates='documents')
  


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

document_roles = Table('document_roles', Base.metadata,
    Column('document_id', UUID(as_uuid=True), ForeignKey('documents.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)