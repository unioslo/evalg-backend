"""
Database models for users
"""
from typing import Dict
import uuid

from sqlalchemy.sql import and_, or_
from sqlalchemy.orm import validates

import evalg.database.types
from evalg import db
from evalg.utils import iterable_but_not_str, make_descriptive_enum, utcnow
from .base import ModelBase


class Person(ModelBase):
    """ Person. """

    __versioned__: Dict = {}

    # Prioritized order of external ids to use when eg creating a voter object
    PREFERRED_IDS = ('feide_id', 'nin')

    id = db.Column(
        evalg.database.types.UuidType,
        primary_key=True,
        default=uuid.uuid4)

    email = db.Column(
        db.UnicodeText,
        index=True)

    display_name = db.Column(
        db.UnicodeText)

    last_update = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    last_update_from_feide = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    principal = db.relationship(
        'PersonPrincipal',
        uselist=False)

    identifiers = db.relationship(
        'PersonExternalId',
        back_populates='person',
        cascade='all, delete-orphan',
        )

    def get_preferred_id(self, *preference):
        """
        Get the first available *preferred* identifier

        :param preference:
            ``PersonExternalId.id_type``s to consider. The first id_type will
            be the *most* preferred.

        :rtype: PersonExternalId
        :return:
            Returns the most preferred ``PersonExternalId`` object, or ``None``
            if the person does not have any of the given id types.
        """
        preferred_ids = preference or self.PREFERRED_IDS

        for obj in sorted(
                (obj for obj in self.identifiers
                 if obj.id_type in preferred_ids),
                key=lambda o: preferred_ids.index(o.id_type)):
            return obj
        return None


PersonIdType = make_descriptive_enum(
    'PersonIdType',
    {
        'feide_id': 'Feide id (eduPersonPrincipalName)',
        'feide_user_id': 'Feide/Dataporten user id',
        'nin': 'National identification number',
        'uid': 'Username',
    },
    description='Person identifier types',
)


class PersonExternalId(ModelBase):
    """ Person external ID. """

    __versioned__: Dict = {}
    __tablename__ = 'person_external_id'

    person_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('person.id'),
        nullable=False)

    id_type = db.Column(
        db.UnicodeText,
        primary_key=True)

    id_value = db.Column(
        db.UnicodeText,
        primary_key=True)

    person = db.relationship(
        'Person',
        back_populates='identifiers')

    @validates('id_type')
    def validate_id_type(self, key, id_type):
        return PersonIdType(id_type).value

    @classmethod
    def find_ids(cls, *where):
        def ensure_iterable(obj):
            if iterable_but_not_str(obj):
                return obj
            return (obj, )

        or_clauses = or_(
            and_(
                cls.id_type == id_type,
                cls.id_value.in_(ensure_iterable(values)),
            )
            for id_type, values in where
        )
        return cls.query.filter(or_clauses)
