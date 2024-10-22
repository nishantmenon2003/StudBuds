"""Add name field to user table

Revision ID: 296d684ccd07
Revises: 65705d7c3e45
Create Date: 2024-10-22 01:44:15.139064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '296d684ccd07'
down_revision = '65705d7c3e45'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('name')

    # ### end Alembic commands ###
