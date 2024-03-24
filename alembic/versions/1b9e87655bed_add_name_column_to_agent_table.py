"""add name column to agent table

Revision ID: 1b9e87655bed
Revises: 419c11f635ca
Create Date: 2024-03-23 11:34:45.648032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b9e87655bed'
down_revision: Union[str, None] = '419c11f635ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('agent_assistant',
    sa.Column('agent_id', sa.UUID(), nullable=False),
    sa.Column('assistant_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['assistant_id'], ['assistants.id'], ),
    sa.PrimaryKeyConstraint('agent_id', 'assistant_id')
    )
    op.add_column('agents', sa.Column('name', sa.String(), nullable=False))
    op.add_column('agents', sa.Column('model', sa.String(length=24), nullable=False))
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_agents_name'), table_name='agents')
    op.drop_column('agents', 'model')
    op.drop_column('agents', 'name')
    op.create_table('spatial_ref_sys',
    sa.Column('srid', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('auth_name', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    sa.Column('auth_srid', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('srtext', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.Column('proj4text', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.CheckConstraint('srid > 0 AND srid <= 998999', name='spatial_ref_sys_srid_check'),
    sa.PrimaryKeyConstraint('srid', name='spatial_ref_sys_pkey')
    )
    op.drop_table('agent_assistant')
    # ### end Alembic commands ###
