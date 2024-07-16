"""adjust event listeners for timestamps to UTC+2

Revision ID: 9bcd7cc0d0e5
Revises: 1b88af689c63
Create Date: 2024-07-16 00:43:48.683976

"""
from typing import Sequence, Union

from sqlalchemy import event

from alembic import op
import sqlalchemy as sa
from database.models import Agent, ChatSession, Document, Module, Role, TokenUsage, Transcript, User
from database.utils import set_created, set_last_modified


# revision identifiers, used by Alembic.
revision: str = '9bcd7cc0d0e5'
down_revision: Union[str, None] = '1b88af689c63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # User table
    op.alter_column('users', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('users', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(User, 'before_insert', set_created)
    event.listen(User, 'before_update', set_last_modified)

    # Role table
    op.alter_column('roles', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('roles', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(Role, 'before_insert', set_created)
    event.listen(Role, 'before_update', set_last_modified)

    # Module table
    op.alter_column('modules', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('modules', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(Module, 'before_insert', set_created)
    event.listen(Module, 'before_update', set_last_modified)

    # TokenUsage table
    op.alter_column('token_usage', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('token_usage', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(TokenUsage, 'before_insert', set_created)
    event.listen(TokenUsage, 'before_update', set_last_modified)

    # Transcript table
    op.alter_column('transcripts', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('transcripts', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(Transcript, 'before_insert', set_created)
    event.listen(Transcript, 'before_update', set_last_modified)

    # ChatSession table
    op.alter_column('chat_sessions', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('chat_sessions', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(ChatSession, 'before_insert', set_created)
    event.listen(ChatSession, 'before_update', set_last_modified)

    # Document table
    op.alter_column('documents', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('documents', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(Document, 'before_insert', set_created)
    event.listen(Document, 'before_update', set_last_modified)

    # Agent table
    op.alter_column('agents', sa.Column('created', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())")))
    op.alter_column('agents', sa.Column('last_modified', sa.DateTime(), nullable=True, server_default=sa.text("timezone('UTC+2', now())"), onupdate=sa.text("timezone('UTC+2', now())")))
    event.listen(Agent, 'before_insert', set_created)
    event.listen(Agent, 'before_update', set_last_modified)

def downgrade():
    # User table
    op.drop_column('users', 'created')
    op.drop_column('users', 'last_modified')
    event.remove(User, 'before_insert', set_created)
    event.remove(User, 'before_update', set_last_modified)

    # Role table
    op.drop_column('roles', 'created')
    op.drop_column('roles', 'last_modified')
    event.remove(Role, 'before_insert', set_created)
    event.remove(Role, 'before_update', set_last_modified)

    # Module table
    op.drop_column('modules', 'created')
    op.drop_column('modules', 'last_modified')
    event.remove(Module, 'before_insert', set_created)
    event.remove(Module, 'before_update', set_last_modified)

    # TokenUsage table
    op.drop_column('token_usage', 'created')
    op.drop_column('token_usage', 'last_modified')
    event.remove(TokenUsage, 'before_insert', set_created)
    event.remove(TokenUsage, 'before_update', set_last_modified)

    # Transcript table
    op.drop_column('transcripts', 'created')
    op.drop_column('transcripts', 'last_modified')
    event.remove(Transcript, 'before_insert', set_created)
    event.remove(Transcript, 'before_update', set_last_modified)

    # ChatSession table
    op.drop_column('chat_sessions', 'created')
    op.drop_column('chat_sessions', 'last_modified')
    event.remove(ChatSession, 'before_insert', set_created)
    event.remove(ChatSession, 'before_update', set_last_modified)

    # Document table
    op.drop_column('documents', 'created')
    op.drop_column('documents', 'last_modified')
    event.remove(Document, 'before_insert', set_created)
    event.remove(Document, 'before_update', set_last_modified)

    # Agent table
    op.drop_column('agents', 'created')
    op.drop_column('agents', 'last_modified')
    event.remove(Agent, 'before_insert', set_created)
    event.remove(Agent, 'before_update', set_last_modified)
