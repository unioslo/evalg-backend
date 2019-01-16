"""
Database models for election candidates.
"""

import uuid

import evalg.models
from evalg import db
from evalg.database.types import NestedMutableJson
from evalg.database.types import URLType
from evalg.database.types import UUIDType


class Candidate(evalg.models.Base):

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4)

    list_id = db.Column(
        UUIDType,
        db.ForeignKey('election_list.id'),
        nullable=False)

    list = db.relationship(
        'ElectionList',
        back_populates='candidates',
        lazy='joined')

    name = db.Column(
        db.UnicodeText,
        nullable=False)

    meta = db.Column(NestedMutableJson)

    information_url = db.Column(URLType)

    priority = db.Column(
        db.Integer,
        default=0)

    pre_cumulated = db.Column(
        db.Boolean,
        default=False)

    user_cumulated = db.Column(
        db.Boolean,
        default=False)

    def _get_repr_fields(self):
        return tuple((
            ('id', self.id),
        ))
