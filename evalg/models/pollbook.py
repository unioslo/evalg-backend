"""
Database model for poll books.

Each poll book is an electorial roll that lists a subset of the registered
voters for a given election.

An individual poll book contains a list of voters for a given election, and
some parameters for how to count votes from these voters.

An election may have multiple poll books. In that case, a person should only be
represented as a voter in *one* of the poll books for that election.

NOTE: There are no constraints that prevents a voter object from being
represented in multiple poll books for a given election.
"""

import uuid

from evalg import db
from evalg.database.types import NestedMutableJson
from evalg.database.types import UuidType
from .base import ModelBase


class Pollbook(ModelBase):

    __versioned__ = {}
    __tablename__ = 'pollbook_meta'

    id = db.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    name = db.Column(NestedMutableJson)

    weight = db.Column(
        db.Integer,
        nullable=False,
        default=1)

    priority = db.Column(
        db.Integer,
        nullable=False,
        default=0)

    election_id = db.Column(
        UuidType,
        db.ForeignKey('election.id'),
        nullable=False)

    election = db.relationship(
        'Election',
        back_populates='pollbooks',
        lazy='joined')

    voters = db.relationship('Voter')

    census_file_imports = db.relationship('CensusFileImport')
