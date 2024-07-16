from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, LargeBinary, Boolean, event
from sqlalchemy.orm import relationship, backref
from database.base import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

from database.utils import set_created, set_last_modified
from util_functions.functions import current_time_prague

# MIGRATING CMDS: alembic revision --autogenerate -m "desc"
# MIGRATING CMDS: alembic upgrade head
# MIGRATE TO SPECIFIC VERSION: alembic upgrade <target-version>
# MANUALLY SET HEAD TO LAST VERSION: alembic stamp head


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
  chat_sessions = relationship('ChatSession', back_populates='user')
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
event.listen(User, 'before_insert', set_created)
event.listen(User, 'before_update', set_last_modified)


class Role(Base):
  __tablename__ = 'roles'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  users = relationship('User', secondary='user_roles', back_populates='roles')
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
event.listen(Role, 'before_insert', set_created)
event.listen(Role, 'before_update', set_last_modified)
  
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
       created = Column(DateTime, default=current_time_prague())
       last_modified = Column(DateTime,
                            default=current_time_prague(),
                            onupdate=current_time_prague())
event.listen(Module, 'before_insert', set_created)
event.listen(Module, 'before_update', set_last_modified)


class TokenUsage(Base):
  __tablename__ = 'token_usage'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  input_tokens = Column(Integer)
  output_tokens = Column(Integer)
  input_cost = Column(Integer)
  output_cost = Column(Integer)
  date = Column(DateTime, default=current_time_prague())
event.listen(TokenUsage, 'before_insert', set_created)
event.listen(TokenUsage, 'before_update', set_last_modified)


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
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
  
event.listen(Transcript, 'before_insert', set_created)
event.listen(Transcript, 'before_update', set_last_modified)


class ChatSession(Base):
  __tablename__ = 'chat_sessions'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  userID = Column(UUID(as_uuid=True),
                  ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True)
  user = relationship('User', back_populates='chat_sessions')
  moduleID = Column(UUID(as_uuid=True),
                    ForeignKey('modules.id', ondelete='SET NULL'),
                    nullable=True)
  module_name = Column(String(25), nullable=True, index=True)
  convo_analytics = Column(Boolean, default=False)
  summaries = Column(Boolean, default=False)
  threadID = Column(String(150), nullable=False, index=True)
  agents = relationship("Agent",
                        secondary='agent_chat',
                        back_populates='chat_sessions')
  summary = Column(String, nullable=True, index=True)
  analysis = Column(String, nullable=True, index=True)
  last_agent = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
  messages_len = Column(Integer, nullable=True, default=0)
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
event.listen(ChatSession, 'before_insert', set_created)
event.listen(ChatSession, 'before_update', set_last_modified)


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
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
event.listen(Document, 'before_insert', set_created)
event.listen(Document, 'before_update', set_last_modified)

# POINTS TO (next agent) --> works only if flow control is AI
class Agent(Base):
  __tablename__ = 'agents'
  id = Column(UUID(as_uuid=True), primary_key=True, index=True)
  name = Column(String, index=True, nullable=False)
  system_prompt = Column(String, nullable=False)
  wrapper_prompt = Column(String, nullable=True)
  initial_prompt = Column(String, nullable=True)
  description = Column(String)
  model = Column(String(24), nullable=False)
  agent_id_pointer = Column(UUID(as_uuid=True), nullable=True)
  documents = relationship("Document",
                           secondary='agent_file',
                           back_populates="agents")
  module_id = Column(UUID(as_uuid=True), ForeignKey('modules.id', ondelete='CASCADE'))
  module = relationship("Module", back_populates='agents')
  director = Column(Boolean, default=False)
  summarizer = Column(Boolean, default=False)
  analytic = Column(Boolean, default=False)
  prompt_chaining = Column(Boolean, default=False)
  chat_sessions = relationship('ChatSession',
                               secondary='agent_chat',
                               back_populates='agents')
  created = Column(DateTime, default=current_time_prague())
  last_modified = Column(DateTime,
                         default=current_time_prague(),
                         onupdate=current_time_prague())
event.listen(Agent, 'before_insert', set_created)
event.listen(Agent, 'before_update', set_last_modified)
  

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

agent_chat_table = Table(
       'agent_chat', Base.metadata,
       Column('agent_id', 
              UUID(as_uuid=True), 
              ForeignKey('agents.id'), 
              primary_key=True),
       Column('chat_session_id', 
              UUID(as_uuid=True), 
              ForeignKey('chat_sessions.id'), 
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