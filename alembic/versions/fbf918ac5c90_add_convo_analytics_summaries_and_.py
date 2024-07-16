"""Add convo_analytics, summaries and module_name columns on chatsession

Revision ID: fbf918ac5c90
Revises: fbc9dd358d99
Create Date: 2024-07-15 17:08:17.018545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbf918ac5c90'
down_revision: Union[str, None] = 'fbc9dd358d99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_sessions', sa.Column('module_name', sa.String(length=25), nullable=True))
    op.add_column('chat_sessions', sa.Column('convo_analytics', sa.Boolean(), nullable=True))
    op.add_column('chat_sessions', sa.Column('summaries', sa.Boolean(), nullable=True))
    op.create_index(op.f('ix_chat_sessions_module_name'), 'chat_sessions', ['module_name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_chat_sessions_module_name'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'summaries')
    op.drop_column('chat_sessions', 'convo_analytics')
    op.drop_column('chat_sessions', 'module_name')
    # ### end Alembic commands ###