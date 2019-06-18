"""
Database model for election results
"""
import uuid

import evalg.database.types
from evalg import db
from .base import ModelBase
from sqlalchemy.orm import deferred


class ElectionResult(ModelBase):

    __versioned__ = {}

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    election_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election.id'))

    election = db.relationship(
        'Election',
        back_populates='election_results',
        lazy='joined')

    election_group_count_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election_group_count.id'))

    election_group_count = db.relationship(
        'ElectionGroupCount',
        back_populates='election_results',
        lazy='joined')

    """ election group count that the result belongs to """

    # TODO: maybe change this to a file column
    election_protocol = deferred(db.Column(evalg.database.types.MutableJson))

    votes = deferred(db.Column(evalg.database.types.MutableJson))
    """ These are deferred to avoid loading too much data """

    result = db.Column(evalg.database.types.MutableJson)

    pollbook_stats = db.Column(evalg.database.types.MutableJson)
