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

    display_name = db.Column(
        db.UnicodeText
    )

    email = db.Column(
        db.UnicodeText,
        index=True)

    feide_id = db.Column(
        db.UnicodeText,
        index=True,
        unique=True)

    first_name = db.Column(
        db.UnicodeText)

    last_name = db.Column(
        db.UnicodeText)

    last_update = db.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow)

    # National Identity Number
    nin = db.Column(
        db.UnicodeText,
        index=True,
        unique=True)

    username = db.Column(
        db.UnicodeText,
        unique=True)

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
