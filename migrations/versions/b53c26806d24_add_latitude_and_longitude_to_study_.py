"""Add latitude and longitude to study_session

Revision ID: b53c26806d24
Revises: d775aed631ac
Create Date: 2024-10-23 05:19:59.168691

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b53c26806d24'
down_revision = 'd775aed631ac'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('study_session') as batch_op:
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('study_session', schema=None) as batch_op:
        batch_op.drop_column('longitude')
        batch_op.drop_column('latitude')

    # ### end Alembic commands ###
