"""Global election group roles

Revision ID: 275f3b23941e
Revises: 2b1a601c9015
Create Date: 2019-09-11 09:32:04.442055

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import and_, or_, column
from sqlalchemy.sql.expression import true, null
import evalg.database.types


# revision identifiers, used by Alembic.
revision = '275f3b23941e'
down_revision = '2b1a601c9015'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('election_group_role', sa.Column('global_role', sa.Boolean(), nullable=True))
    op.add_column('election_group_role_version', sa.Column('global_role', sa.Boolean(), autoincrement=False, nullable=True))
    op.add_column('election_group_role_version', sa.Column('global_role_mod', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    op.create_check_constraint(
        'no_eg_when_global',
        'election_group_role',
        or_(
            and_(
                column('global_role') == true(),
                column('group_id') == null()),
            column('global_role') == null())
    )


def downgrade():
    op.drop_constraint(
        'no_eg_when_global',
        'election_group_role',
        type_='check')
    op.drop_column('election_group_role_version', 'global_role_mod')
    op.drop_column('election_group_role_version', 'global_role')
    op.drop_column('election_group_role', 'global_role')


