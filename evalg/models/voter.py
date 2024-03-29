"""
Database model for voter registration.

Each voter object should represent a persons right to vote in an election.
Voters are tied to the election through *poll books*.

Note that voter objects are not re-used across different elections. Each person
should be represented by a *unique* voter object for each election they are
entitled to vote in.
"""
from typing import Dict
import uuid

import sqlalchemy.types
from sqlalchemy import case, exists, select
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint, CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from evalg import db
from evalg.models.person import PersonIdType
from evalg.models.votes import Vote
from evalg.utils import make_descriptive_enum
from evalg.database.types import UuidType
from .base import ModelBase


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
VERIFIED_STATUS_MAP = {
    (True, False, False): VerifiedStatus.SELF_ADDED_NOT_REVIEWED,
    (False, True, False): VerifiedStatus.ADMIN_ADDED_REJECTED,
    (True, True, False): VerifiedStatus.SELF_ADDED_REJECTED,
    (False, False, True): VerifiedStatus.ADMIN_ADDED_AUTO_VERIFIED,
    (True, True, True): VerifiedStatus.SELF_ADDED_VERIFIED}

# Invalid combinations of (self_added, reviewed, verified)
# Manually update `verified_status_check_constraint` if changed
VERIFIED_STATUS_NO_MAP = (
    (True, False, True),
    (False, True, True),
    (False, False, False)
)


class Voter(ModelBase):
    """Voter / census member model."""

    __versioned__: Dict = {}
    __tablename__ = 'pollbook_voters'

    id = sqlalchemy.schema.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

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
        'Pollbook',
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

    votes = db.relationship('Vote', cascade='all, delete-orphan')
    records = db.relationship('VoteRecord', cascade='all, delete-orphan')

    reason = sqlalchemy.schema.Column(
        sqlalchemy.types.UnicodeText,
        doc='reason why this voter should be included in the pollbook',
        nullable=True)

    def is_valid_voter(self):
        """
        Checks if the voter is a valid one.

        Valid voters have the status ADMIN_ADDED_AUTO_VERIFIED or
        SELF_ADDED_VERIFIED
        """
        if (self.verified_status == VerifiedStatus.ADMIN_ADDED_AUTO_VERIFIED or
                self.verified_status == VerifiedStatus.SELF_ADDED_VERIFIED):
            return True
        return False

    def ensure_rereview(self):
        """Ensure that the admin need to make a new review of the voter."""
        if self.verified_status is VerifiedStatus.SELF_ADDED_REJECTED:
            self.reviewed = False

    def undo_review(self):
        if self.verified_status in (VerifiedStatus.SELF_ADDED_VERIFIED,
                                    VerifiedStatus.SELF_ADDED_REJECTED):
            self.reviewed = False
            self.verified = False
        elif self.verified_status is VerifiedStatus.ADMIN_ADDED_REJECTED:
            self.reviewed = False
            self.verified = True

    @hybrid_property
    def has_voted(self):
        """Has the voter voted."""
        return len(self.votes) > 0

    @has_voted.expression # type: ignore
    def has_voted(cls):
        """has_voted sqlalchemy expression."""
        return (
            select([
                case([(exists().where(and_(
                    Vote.voter_id == cls.id,
                )).correlate(cls), True)],
                    else_=False,
                ).label("has_votes")
            ]).label("number_has_votes"))

    @hybrid_property
    def verified_status(self):
        return VERIFIED_STATUS_MAP[(self.self_added,
                                    self.reviewed,
                                    self.verified)]

    verified_status_check_constraint = not_(or_(
        and_(self_added.is_(True), reviewed.is_(False), verified.is_(True)),
        and_(self_added.is_(False), reviewed.is_(True), verified.is_(True)),
        and_(self_added.is_(False), reviewed.is_(False), verified.is_(False))
    ))

    #
    # TODO: Get ID_TYPE_CHOICES from PersonExternalId, or implement a separate
    # set of id types? We may not want to support dp_user_id or uid here?
    #
    @validates('id_type')
    def validate_id_type(self, key, id_type):
        return PersonIdType(id_type).value

    __table_args__ = (
        UniqueConstraint(
            'pollbook_id', 'id_type', 'id_value',
            name='_pollbook_voter_uc'),
        CheckConstraint(
            verified_status_check_constraint,
            name='_pollbook_voter_cc_verified_status'
        )
    )
