"""add images column to document table

Revision ID: 4c3de3af733f
Revises: 7f0fa7e01adc
Create Date: 2024-08-06 14:25:37.085625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c3de3af733f'
down_revision: Union[str, None] = '7f0fa7e01adc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('documents', sa.Column('images', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('documents', 'images')
    # ### end Alembic commands ###
