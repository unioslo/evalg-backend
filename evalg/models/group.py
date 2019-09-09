"""
Database models for groups of users.
"""

import uuid

# from sqlalchemy.orm import relationship
# from sqlalchemy.schema import Column
from sqlalchemy import schema

import evalg.database.types
from evalg import db
from evalg.utils import utcnow
from .base import ModelBase


class Group(ModelBase):
    """ Group of persons. """

    __versioned__ = {}

    id = db.Column(
        evalg.database.types.UuidType,
        primary_key=True,
        default=uuid.uuid4)

    dp_group_id = db.Column(
        db.UnicodeText,
        index=True)

    name = db.Column(
        db.UnicodeText,
        unique=True,
        nullable=False)

    last_update = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    principals = db.relationship('GroupPrincipal')

    external_ids = db.relationship(
        'GroupExternalID',
        back_populates='group')


class GroupExternalIDType(ModelBase):
    """ Group external ID type. """

    __versioned__ = {}

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)


class GroupExternalID(ModelBase):
    """ Group external ID. """

    __versioned__ = {}
    __tablename__ = 'group_external_id'

    group_id = db.Column(
        evalg.database.types.UuidType,
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


class GroupMembership(ModelBase):
    """ Group memberships. """

    __versioned__ = {}

    id = db.Column(
        evalg.database.types.UuidType,
        primary_key=True,
        default=uuid.uuid4)

    group_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('group.id'),
        nullable=False)

    person_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('person.id'),
        nullable=False)

    __table_args__ = (schema.UniqueConstraint(
        'group_id',
        'person_id'),)
