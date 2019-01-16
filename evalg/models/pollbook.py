#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Models for poll books. """

import uuid

import evalg.models
from evalg import db
from evalg.database.types import NestedMutableJson
from evalg.database.types import UUIDType


class PollBook(evalg.models.Base):
    """ Poll book / census. """

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4)

    name = db.Column(NestedMutableJson)

    weight = db.Column(
        db.Integer,
        nullable=False,
        default=1)

    priority = db.Column(
        db.Integer,
        nullable=False,
        default=0)

    election_id = db.Column(
        UUIDType,
        db.ForeignKey('election.id'),
        nullable=False)

    election = db.relationship(
        'Election',
        back_populates='pollbooks',
        lazy='joined')

    voters = db.relationship('Voter')

    def _get_repr_fields(self):
        return tuple((
            ('id', self.id),
        ))
