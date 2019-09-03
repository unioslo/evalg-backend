"""
Database model for election results
"""
import uuid

from sqlalchemy.orm import deferred

import evalg.database.types
from evalg import db
from evalg.counting import count

from .base import ModelBase


class ElectionResult(ModelBase):
    """The ElectionResult class"""
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

    ballots = deferred(db.Column(evalg.database.types.NestedMutableJson))
    """ These are deferred to avoid loading too much data """

    result = db.Column(evalg.database.types.MutableJson)

    pollbook_stats = db.Column(evalg.database.types.MutableJson)

    @property
    def election_protocol_text(self):
        """election_protocol_text-property"""
        try:
            protcol_cls = count.PROTOCOL_MAPPINGS[self.election.type_str]
            return protcol_cls.from_dict(self.election_protocol).render()
        except KeyError:
            # re-raise?
            return 'Unsupported counting method for protocol'
        return self.value
