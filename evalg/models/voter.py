#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Models for voters. """

import uuid

from evalg import db
from evalg.database.types import UUIDType
from evalg.models import Base


class VoterStatus(Base):
    """ Voter / census member status code model. """

    code = db.Column(
        db.UnicodeText,
        primary_key=True)

    description = db.Column(db.UnicodeText)

    def _get_repr_fields(self):
        return tuple((
            ('code', self.code),
        ))


class Voter(Base):
    """ Voter / census member model."""

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4)

    tag = db.Column(db.UnicodeText)

    person_id = db.Column(
        UUIDType,
        db.ForeignKey('person.id'),
        nullable=False)

    person = db.relationship('Person')

    pollbook_id = db.Column(
        UUIDType,
        db.ForeignKey('poll_book.id'),
        nullable=False)

    pollbook = db.relationship(
        'PollBook',
        back_populates='voters')

    voter_status_id = db.Column(
        db.UnicodeText,
        db.ForeignKey('voter_status.code'),
        nullable=False)

    voter_status = db.relationship('VoterStatus')  # no bakref needed

    def _get_repr_fields(self):
        return tuple((
            ('id', self.id),
        ))
