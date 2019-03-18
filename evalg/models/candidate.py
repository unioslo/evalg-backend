"""
Database models for election candidates.
"""

import uuid

from evalg import db
from evalg.database.types import NestedMutableJson
from evalg.database.types import UrlType
from evalg.database.types import UuidType
from .base import ModelBase


class Candidate(ModelBase):

    __versioned__ = {}

    id = db.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    list_id = db.Column(
        UuidType,
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

    information_url = db.Column(UrlType)

    priority = db.Column(
        db.Integer,
        default=0)

    pre_cumulated = db.Column(
        db.Boolean,
        default=False)

    user_cumulated = db.Column(
        db.Boolean,
        default=False)
