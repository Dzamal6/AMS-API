"""add assistant file relationship to assistants table

Revision ID: 06563ff5e4f0
Revises: 951cdcc81431
Create Date: 2024-05-08 13:26:06.804277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06563ff5e4f0'
down_revision: Union[str, None] = '951cdcc81431'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
