"""Add profile_picture field to user

Revision ID: 90dd2049b324
Revises: 296d684ccd07
Create Date: 2024-10-22 02:01:42.835488

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90dd2049b324'
down_revision = '296d684ccd07'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_picture')

    # ### end Alembic commands ###
