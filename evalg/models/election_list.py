"""
Database models for candidate lists.
"""
import uuid

from evalg import db
from evalg.database.types import NestedMutableJson
from evalg.database.types import UrlType
from evalg.database.types import UuidType
from .base import ModelBase


class ElectionList(ModelBase):
    """ List of electable candidates in an election. """

    id = db.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    name = db.Column(NestedMutableJson)

    description = db.Column(NestedMutableJson)

    information_url = db.Column(UrlType)

    election_id = db.Column(
        UuidType,
        db.ForeignKey('election.id'),
        nullable=False)

    election = db.relationship(
        'Election',
        back_populates='lists',
        lazy='joined')

    candidates = db.relationship('Candidate')
