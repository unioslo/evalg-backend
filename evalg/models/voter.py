"""
Database model for voter registration.

Each voter object should represent a persons right to vote in an election.
Voters are tied to the election through *poll books*.

Note that voter objects are not re-used across different elections. Each person
should be represented by a *unique* voter object for each election they are
entitled to vote in.
"""
import uuid

from sqlalchemy.schema import UniqueConstraint

from evalg import db
from evalg.database.types import UuidType
from .base import ModelBase


class VoterStatus(ModelBase):
    """ Voter / census member status code model. """

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)


class Voter(ModelBase):
    """ Voter / census member model."""

    id = db.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    tag = db.Column(db.UnicodeText)

    person_id = db.Column(
        UuidType,
        db.ForeignKey('person.id'),
        nullable=False)

    person = db.relationship('Person')

    pollbook_id = db.Column(
        UuidType,
        db.ForeignKey('poll_book.id'),
        nullable=False)

    pollbook = db.relationship(
        'PollBook',
        back_populates='voters')

    voter_status_id = db.Column(
        db.UnicodeText,
        db.ForeignKey('voter_status.code'),
        nullable=False)

    voter_status = db.relationship('VoterStatus')  # no bakref needed

    votes = db.relationship('Vote')

    __table_args__ = (
        UniqueConstraint('person_id', 'pollbook_id', name='_person_pollbook_uc'),
    )
