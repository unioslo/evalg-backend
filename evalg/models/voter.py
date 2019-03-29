"""
Database model for voter registration.

Each voter object should represent a persons right to vote in an election.
Voters are tied to the election through *poll books*.

Note that voter objects are not re-used across different elections. Each person
should be represented by a *unique* voter object for each election they are
entitled to vote in.
"""
import uuid
from enum import Enum

import sqlalchemy.types
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from evalg import db
from evalg.database.types import UuidType
from .base import ModelBase
from .person import IdType


class VerifiedStatus(Enum):
    SELF_ADDED_NOT_REVIEWED = 1
    ADMIN_ADDED_REJECTED = 2
    SELF_ADDED_REJECTED = 3
    ADMIN_ADDED_AUTO_VERIFIED = 4
    SELF_ADDED_VERIFIED = 7

    @property
    def description(self):
        if self == VerifiedStatus.SELF_ADDED_NOT_REVIEWED:
            return 'voter not in census, admin review needed'
        if self == VerifiedStatus.ADMIN_ADDED_REJECTED:
            return 'voter in census, rejected by admin'
        if self == VerifiedStatus.SELF_ADDED_REJECTED:
            return 'voter not in census, rejected by admin'
        if self == VerifiedStatus.ADMIN_ADDED_AUTO_VERIFIED:
            return 'voter in census'
        if self == VerifiedStatus.SELF_ADDED_VERIFIED:
            return 'voter not in census, verified by admin'


# Mapping (manual, reviewed, verified) to VerifiedStatus
db_values2verified_status = {
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
        return db_values2verified_status[(self.self_added,
                                          self.reviewed,
                                          self.verified)]

    #
    # TODO: Get ID_TYPE_CHOICES from PersonExternalId, or implement a separate
    # set of id types? We may not want to support dp_user_id or uid here?
    #
    @validates('id_type')
    def validate_id_type(self, key, id_type):
        return IdType(id_type).value

    @validates('self_added', 'reviewed', 'verified')
    def validate_verified_status(self, key, value):
        current_values = dict(self_added=self.self_added,
                              reviewed=self.reviewed,
                              verified=self.verified)

        # Don't throw error if a column doesn't have a value yet
        if any(value is None for value in current_values.values()):
            return value

        current_values[key] = value
        new_values = tuple(current_values.values())
        if not db_values2verified_status.get(new_values):
            raise ValueError(
                'Unvalid combination of values given for columns `{}`, `{}`, '
                '`{}`, ({}, {}, {})'.format(*current_values.keys(),
                                            *current_values.values()))
        return value

    __table_args__ = (
        UniqueConstraint(
            'pollbook_id', 'id_type', 'id_value',
            name='_pollbook_voter_uc'),
    )
