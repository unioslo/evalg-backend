"""remove-ballot-type

Revision ID: e0c99670d3b4
Revises: 9f52391919e5
Create Date: 2019-09-11 12:33:34.415753

"""
from alembic import op
import sqlalchemy as sa
import evalg.database.types


# revision identifiers, used by Alembic.
revision = 'e0c99670d3b4'
down_revision = 'cc2a0e03e20a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ballots', 'ballot_type')
    op.drop_column('ballots_version', 'ballot_type_mod')
    op.drop_column('ballots_version', 'ballot_type')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ballots_version', sa.Column('ballot_type', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('ballots_version', sa.Column('ballot_type_mod', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('ballots', sa.Column('ballot_type', sa.TEXT(), autoincrement=False, nullable=False, server_default='temp'))
    op.alter_column('ballots', 'ballot_type', server_default=None)
    # ### end Alembic commands ###