"""
Database model for election group count
"""
import uuid

from sqlalchemy.sql import case
from sqlalchemy.ext.hybrid import hybrid_property

import evalg.database.types
from evalg import db
from .base import ModelBase


class ElectionGroupCount(ModelBase):

    __versioned__ = {}

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    group_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election_group.id'))

    election_group = db.relationship(
        'ElectionGroup',
        back_populates='election_group_counts',
        lazy='joined')

    election_results = db.relationship('ElectionResult')

    initiated_at = db.Column(evalg.database.types.UtcDateTime)

    finished_at = db.Column(evalg.database.types.UtcDateTime)

    audit = db.Column(evalg.database.types.MutableJson)

    @hybrid_property
    def status(self):
        if self.finished_at:
            return 'finished'
        return 'ongoing'

    @status.expression
    def status(cls):
        return case(
            [(cls.finished_at.isnot(None), 'finished')],
            else_='ongoing')
