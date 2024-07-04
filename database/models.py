from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, LargeBinary, Boolean
from sqlalchemy.orm import relationship, backref
from database.base import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

# MIGRATING CMDS: alembic revision --autogenerate -m "desc"
# MIGRATING CMDS: alembic upgrade head
# MIGRATE TO SPECIFIC VERSION: alembic upgrade <target-version>


class User(Base):
  __tablename__ = 'users'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  username = Column(String(30), unique=True, index=True)
  email = Column(String(30), unique=True, index=True)
  password_hash = Column(String(255), nullable=True)
  roles = relationship('Role', secondary='user_roles', back_populates='users')
  modules = relationship('Module',
                            secondary='user_module',
                            back_populates='users')
  transcripts = relationship('Transcript', backref='user', lazy='dynamic')
  chat_sessions = relationship('ChatSession', backref='user', lazy='dynamic')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class Role(Base):
  __tablename__ = 'roles'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  users = relationship('User', secondary='user_roles', back_populates='roles')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)
  
class Module(Base):
       __tablename__ = 'modules'
       id = Column(UUID(as_uuid=True), primary_key=True, index=True)
       name = Column(String(30), unique=True, index=True)
       description = Column(String(200), unique=False, index=True)
       flow_control = Column(String(10), unique=False, index=True)
       voice = Column(Boolean, default=False)
       convo_analytics = Column(Boolean, default=False)
       summaries = Column(Boolean, default=False)
       users = relationship('User',
                            secondary='user_module',
                            back_populates='modules')
       documents = relationship("Document",
                            secondary='document_module',
                            back_populates="modules",)
       agents = relationship('Agent', back_populates='module', cascade='all, delete-orphan')
       created = Column(DateTime, default=datetime.utcnow)
       last_modified = Column(DateTime,
                            default=datetime.utcnow,
                            onupdate=datetime.utcnow)


class TokenUsage(Base):
  __tablename__ = 'token_usage'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  input_tokens = Column(Integer)
  output_tokens = Column(Integer)
  input_cost = Column(Integer)
  output_cost = Column(Integer)
  date = Column(DateTime, default=datetime.utcnow)


class Transcript(Base):
  __tablename__ = 'transcripts'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  transcriptID = Column(String, unique=True, index=True)
  sessionID = Column(UUID(as_uuid=True),
                     ForeignKey('chat_sessions.id', ondelete='CASCADE'),
                     nullable=False)
  userID = Column(UUID(as_uuid=True),
                  ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True)
  username = Column(String, nullable=False)
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class ChatSession(Base):
  __tablename__ = 'chat_sessions'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  userID = Column(UUID(as_uuid=True),
                  ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True)
  moduleID = Column(UUID(as_uuid=True),
                    ForeignKey('modules.id', ondelete='SET NULL'),
                    nullable=True)
  transcripts = relationship('Transcript',
                             backref='chat_session',
                             lazy='dynamic',
                             cascade='all, delete-orphan')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class Document(Base):
  __tablename__ = "documents"
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String)
  content = Column(LargeBinary)
  content_hash = Column(String(64), unique=True)
  agents = relationship("Agent",
                        secondary='agent_file',
                        back_populates='documents')
  modules = relationship("Module", secondary='document_module', back_populates='documents')
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class Agent(Base):
  __tablename__ = 'agents'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, index=True, nullable=False)
  system_prompt = Column(String, nullable=False)
  wrapper_prompt = Column(String, nullable=True)
  description = Column(String)
  model = Column(String(24), nullable=False)
  documents = relationship("Document",
                           secondary='agent_file',
                           back_populates="agents")
  module_id = Column(UUID(as_uuid=True), ForeignKey('modules.id', ondelete='CASCADE'))
  module = relationship("Module", back_populates='agents')
  director = Column(Boolean, default=False)
  prompt_chaining = Column(Boolean, default=False)
  created = Column(DateTime, default=datetime.utcnow)
  last_modified = Column(DateTime,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)
  

agent_file_table = Table(
    'agent_file', Base.metadata,
    Column('agent_id',
           UUID(as_uuid=True),
           ForeignKey('agents.id'),
           primary_key=True),
    Column('document_id',
           UUID(as_uuid=True),
           ForeignKey('documents.id'),
           primary_key=True))

# can be changed to agent
# assistant_usage = Table(
#     'assistant_usage', Base.metadata,
#     Column('assistant_id',
#            UUID(as_uuid=True),
#            ForeignKey('assistants.id'),
#            primary_key=True),
#     Column('token_usage_id',
#            UUID(as_uuid=True),
#            ForeignKey('token_usage.id'),
#            primary_key=True))

user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id',
           UUID(as_uuid=True),
           ForeignKey('users.id'),
           primary_key=True),
    Column('role_id',
           UUID(as_uuid=True),
           ForeignKey('roles.id'),
           primary_key=True))

### MODULES TRANSITION

document_module_table = Table(
       'document_module', Base.metadata,
       Column('document_id',
              UUID(as_uuid=True),
              ForeignKey('documents.id', ondelete='CASCADE'),
              primary_key=True),
       Column('module_id',
              UUID(as_uuid=True),
              ForeignKey('modules.id', ondelete='CASCADE'),
              primary_key=True))

user_module_table = Table(
       'user_module', Base.metadata,
       Column('user_id',
              UUID(as_uuid=True),
              ForeignKey('users.id'),
              primary_key=True),
       Column('module_id',
              UUID(as_uuid=True),
              ForeignKey('modules.id'),
              primary_key=True))