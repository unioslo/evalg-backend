"""
Database models for users
"""

import uuid

from sqlalchemy.sql import and_, or_
from sqlalchemy.orm import validates

import evalg.database.types
from evalg import db
from evalg.utils import iterable_but_not_str, utcnow
from .base import ModelBase


class Person(ModelBase):
    """ Person. """

    id = db.Column(
        evalg.database.types.UuidType,
        primary_key=True,
        default=uuid.uuid4)

    email = db.Column(
        db.UnicodeText,
        index=True)

    first_name = db.Column(
        db.UnicodeText,
        nullable=False)

    last_name = db.Column(
        db.UnicodeText,
        nullable=False)

    display_name = db.Column(
        db.UnicodeText,
        nullable=False)

    last_update = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    last_update_from_feide = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    principals = db.relationship('PersonPrincipal')

    external_ids = db.relationship(
        'PersonExternalId',
        back_populates='person',
        cascade='all, delete-orphan')

class PersonExternalId(ModelBase):
    """ Person external ID. """

    __tablename__ = 'person_external_id'

    ID_TYPE_CHOICES = {
        'nin': 'National identification number',
        'uid': 'Username',
        'dp_user_id': 'Dataporten user ID',
        'feide_id': 'Feide ID',
    }

    person_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('person.id'),
        nullable=False)

    id_type = db.Column(
        db.UnicodeText,
        primary_key=True)

    external_id = db.Column(
        db.UnicodeText,
        primary_key=True)

    person = db.relationship(
        'Person',
        back_populates='external_ids')

    @validates('id_type')
    def validate_id_type(self, key, id_type):
        assert id_type in self.ID_TYPE_CHOICES
        return id_type

    @classmethod
    def find_ids(cls, *where):
        def ensure_iterable(obj):
            if iterable_but_not_str(obj):
                return obj
            return (obj, )

        or_clauses = or_(
            and_(
                cls.id_type == id_type,
                cls.external_id.in_(ensure_iterable(values)),
            )
            for id_type, values in where
        )
        return cls.query.filter(or_clauses)
