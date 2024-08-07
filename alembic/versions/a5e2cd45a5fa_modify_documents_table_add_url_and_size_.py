"""Modify Documents table --> add url and size columns

Revision ID: a5e2cd45a5fa
Revises: 9bcd7cc0d0e5
Create Date: 2024-07-28 18:19:18.262194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a5e2cd45a5fa'
down_revision: Union[str, None] = '9bcd7cc0d0e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('documents', sa.Column('url', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('size', sa.Integer(), nullable=True))
    op.drop_constraint('documents_content_hash_key', 'documents', type_='unique')
    op.create_index(op.f('ix_documents_name'), 'documents', ['name'], unique=False)
    op.drop_column('documents', 'content')
    op.drop_column('documents', 'content_hash')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('documents', sa.Column('content_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.add_column('documents', sa.Column('content', postgresql.BYTEA(), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_documents_name'), table_name='documents')
    op.create_unique_constraint('documents_content_hash_key', 'documents', ['content_hash'])
    op.drop_column('documents', 'size')
    op.drop_column('documents', 'url')
    # ### end Alembic commands ###
