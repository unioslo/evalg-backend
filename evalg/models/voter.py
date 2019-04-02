"""
Database model for voter registration.

Each voter object should represent a persons right to vote in an election.
Voters are tied to the election through *poll books*.

Note that voter objects are not re-used across different elections. Each person
should be represented by a *unique* voter object for each election they are
entitled to vote in.
"""
import uuid

import sqlalchemy.types
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint, CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from evalg import db
from evalg.utils import make_descriptive_enum
from evalg.database.types import UuidType
from .base import ModelBase
from .person import IdType


VerifiedStatus = make_descriptive_enum(
    'VerifiedStatus',
    {
        'SELF_ADDED_NOT_REVIEWED': 'voter not in census, admin review needed',
        'ADMIN_ADDED_REJECTED': 'voter in census, rejected by admin',
        'SELF_ADDED_REJECTED': 'voter not in census, rejected by admin',
        'ADMIN_ADDED_AUTO_VERIFIED': 'voter in census',
        'SELF_ADDED_VERIFIED': 'voter not in census, verified by admin',
    },
    description='Voter verification status',
)


# Mapping (self_added, reviewed, verified) to VerifiedStatus
verified_status = {
    (True, False, False): VerifiedStatus.SELF_ADDED_NOT_REVIEWED,
    (False, True, False): VerifiedStatus.ADMIN_ADDED_REJECTED,
    (True, True, False): VerifiedStatus.SELF_ADDED_REJECTED,
    (False, False, True): VerifiedStatus.ADMIN_ADDED_AUTO_VERIFIED,
    (True, True, True): VerifiedStatus.SELF_ADDED_VERIFIED}


class Voter(ModelBase):
    """ Voter / census member model."""

    __versioned__ = {}
    __tablename__ = 'pollbook_voters'

    id = sqlalchemy.schema.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    tag = sqlalchemy.schema.Column(
        sqlalchemy.types.UnicodeText,
        doc='TODO: what is this used for?',
    )

    id_type = sqlalchemy.schema.Column(
        sqlalchemy.types.UnicodeText,
        doc='person identifier type',
        nullable=False,
    )

    id_value = sqlalchemy.schema.Column(
        sqlalchemy.types.UnicodeText,
        doc='person identifier value',
        nullable=False,
    )

    pollbook_id = sqlalchemy.schema.Column(
        UuidType,
        db.ForeignKey('pollbook_meta.id'),
        nullable=False)

    pollbook = db.relationship(
        'PollBook',
        back_populates='voters')

    self_added = db.Column(
        sqlalchemy.types.Boolean,
        doc='voter was added to the poll book by himself',
        nullable=False)

    reviewed = db.Column(
        sqlalchemy.types.Boolean,
        doc='voter has been reviewed by admin',
        nullable=False)

    verified = sqlalchemy.schema.Column(
        sqlalchemy.types.Boolean,
        doc='voter is verified, and any vote should be counted',
        nullable=False)

    votes = db.relationship('Vote')

    reason = sqlalchemy.schema.Column(
        sqlalchemy.types.UnicodeText,
        doc='reason why this voter should be included in the pollbook',
        nullable=True)

    @hybrid_property
    def verified_status(self):
        return verified_status[(self.self_added,
                                self.reviewed,
                                self.verified)]

    #
    # TODO: Get ID_TYPE_CHOICES from PersonExternalId, or implement a separate
    # set of id types? We may not want to support dp_user_id or uid here?
    #
    @validates('id_type')
    def validate_id_type(self, key, id_type):
        return IdType(id_type).value

    @staticmethod
    def verified_status_check_constraint():
        """Get a CheckConstraint for self_added, reviewed and verified

        :return: A CheckConstraint equivalent to:
            (self_added, reviewed, verified) in verified_status
        """
        names = ('self_added', 'reviewed', 'verified')
        valid_combinations = tuple(verified_status.keys())
        last_col = {len(names) - 1: ') '}
        last_row = {len(valid_combinations) - 1: ''}
        constraint = ''

        for row in range(len(valid_combinations)):
            constraint += '('
            for col in range(len(names)):
                constraint += names[col] + \
                    ' = ' + \
                    'cast(' + str(int(valid_combinations[row][col])) + ' as boolean)' + \
                    last_col.get(col, ' AND ')
            constraint += last_row.get(row, ' OR ')
        return CheckConstraint(constraint)

    __table_args__ = (
        UniqueConstraint(
            'pollbook_id', 'id_type', 'id_value',
            name='_pollbook_voter_uc'),
        verified_status_check_constraint.__func__()
    )
