"""
Database models for users
"""

import uuid

import evalg.database.types
import evalg.models
from evalg import db
from evalg.utils import utcnow


class Person(evalg.models.Base):
    """ Person. """

    id = db.Column(
        evalg.database.types.UuidType,
        primary_key=True,
        default=uuid.uuid4)

    dp_user_id = db.Column(
        db.UnicodeText,
        index=True)

    email = db.Column(
        db.UnicodeText,
        index=True)

    feide_id = db.Column(
        db.UnicodeText,
        index=True)

    first_name = db.Column(
        db.UnicodeText,
        nullable=False)

    last_name = db.Column(
        db.UnicodeText,
        nullable=False)

    last_update = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    # National Identity Number
    nin = db.Column(
        db.UnicodeText,
        index=True,
        nullable=False)

    username = db.Column(db.UnicodeText)

    principals = db.relationship('PersonPrincipal')

    external_ids = db.relationship(
        'PersonExternalID',
        back_populates='person')


class PersonExternalIDType(evalg.models.Base):
    """ Person external ID type. """

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)


class PersonExternalID(evalg.models.Base):
    """ Person external ID. """

    __tablename__ = 'person_external_id'

    person_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('person.id'),
        nullable=False)

    external_id = db.Column(
        db.UnicodeText,
        primary_key=True)

    type_code = db.Column(
        db.UnicodeText,
        db.ForeignKey('person_external_id_type.code'),
        primary_key=True)

    person = db.relationship(
        'Person',
        back_populates='external_ids')

    id_type = db.relationship('PersonExternalIDType')  # no b.ref needed
