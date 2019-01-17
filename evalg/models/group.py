"""
Database models for groups of users.
"""

import datetime
import uuid


import evalg.models
from evalg import db
from evalg.database.types import UuidType


class Group(evalg.models.Base):
    """ Group of persons. """

    id = db.Column(
        UuidType,
        primary_key=True,
        default=uuid.uuid4)

    dp_group_id = db.Column(
        db.UnicodeText,
        index=True)

    name = db.Column(
        db.UnicodeText,
        nullable=False)

    last_update = db.Column(
        db.DateTime,
        default=datetime.datetime.now)

    principals = db.relationship('GroupPrincipal')

    external_ids = db.relationship(
        'GroupExternalID',
        back_populates='group')

    def _get_repr_fields(self):
        return tuple((
            ('id', self.id),
        ))


class GroupExternalIDType(evalg.models.Base):
    """ Group external ID type. """

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)

    def _get_repr_fields(self):
        return tuple((
            ('code', self.code),
        ))


class GroupExternalID(evalg.models.Base):
    """ Group external ID. """

    __tablename__ = 'group_external_id'

    group_id = db.Column(
        UuidType,
        db.ForeignKey('group.id'),
        nullable=False)

    external_id = db.Column(
        db.UnicodeText,
        primary_key=True)

    type_code = db.Column(
        db.UnicodeText,
        db.ForeignKey('group_external_id_type.code'),
        primary_key=True)

    group = db.relationship(
        'Group',
        back_populates='external_ids')

    id_type = db.relationship('GroupExternalIDType')  # no b.ref needed

    def _get_repr_fields(self):
        return tuple((
            ('group_id', self.group_id),
            ('type_code', self.type_code),
            ('external_id', self.external_id),
        ))
