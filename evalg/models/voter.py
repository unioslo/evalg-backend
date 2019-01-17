""" Models for voters. """

import uuid

from evalg import db
from evalg.database.types import UuidType
from evalg.models import Base

from sqlalchemy.schema import UniqueConstraint


class VoterStatus(Base):
    """ Voter / census member status code model. """

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)

    def _get_repr_fields(self):
        return tuple((
            ('code', self.code),
        ))


class Voter(Base):
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

    __table_args__ = (UniqueConstraint('person_id', 'pollbook_id', name='_person_pollbook_uc'),)

    def _get_repr_fields(self):
        return tuple((
            ('id', self.id),
        ))
