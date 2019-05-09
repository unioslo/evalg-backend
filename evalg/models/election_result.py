"""
Database model for election results
"""
import uuid

import evalg.database.types
from evalg import db
from .base import ModelBase


class ElectionResult(ModelBase):

    __versioned__ = {}

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    election_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election.id'))

    group = db.relationship(
        'ElectionGroupCount',
        back_populates='election_results',
        lazy='joined')

    election = db.relationship(
        'Election',
        back_populates='election_results',
        lazy='joined')

    count_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election_group_count.id'))
    """ election group count that the result belongs to """

    # TODO: maybe change this to a file column
    path_to_election_protocol = db.Column(db.UnicodeText)

    votes = db.Column(evalg.database.types.MutableJson)

    result = db.Column(evalg.database.types.MutableJson)
