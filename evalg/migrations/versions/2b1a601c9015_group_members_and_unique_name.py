"""group members and unique name

Revision ID: 2b1a601c9015
Revises: 9f52391919e5
Create Date: 2019-09-09 12:33:25.764923

"""
from alembic import op
import sqlalchemy as sa
import evalg.database.types


# revision identifiers, used by Alembic.
revision = '2b1a601c9015'
down_revision = '9f52391919e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('group_membership_version',
    sa.Column('id', evalg.database.types.UuidType(), autoincrement=False, nullable=False),
    sa.Column('group_id', evalg.database.types.UuidType(), autoincrement=False, nullable=True),
    sa.Column('person_id', evalg.database.types.UuidType(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.Column('group_id_mod', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('person_id_mod', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_group_membership_version_end_transaction_id'), 'group_membership_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_group_membership_version_operation_type'), 'group_membership_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_group_membership_version_transaction_id'), 'group_membership_version', ['transaction_id'], unique=False)
    op.create_table('group_membership',
    sa.Column('id', evalg.database.types.UuidType(), nullable=False),
    sa.Column('group_id', evalg.database.types.UuidType(), nullable=False),
    sa.Column('person_id', evalg.database.types.UuidType(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['group.id'], ),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'person_id')
    )
    op.create_unique_constraint('uix_group_unique_name', 'group', ['name'])


def downgrade():
    op.drop_constraint('uix_group_unique_name', 'group', type_='unique')
    op.drop_table('group_membership')
    op.drop_index(op.f('ix_group_membership_version_transaction_id'), table_name='group_membership_version')
    op.drop_index(op.f('ix_group_membership_version_operation_type'), table_name='group_membership_version')
    op.drop_index(op.f('ix_group_membership_version_end_transaction_id'), table_name='group_membership_version')
    op.drop_table('group_membership_version')
