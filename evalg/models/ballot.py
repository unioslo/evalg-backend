"""
Database models for ballots.

This module defines a single object, py:class:`Envelope`, which is a simple
uuid -> binary data mapping.  Along with the binary data are some parameters on
how the binary data is encoded.

To leave a ballot, the process should be as follows:

1. Ballot data in the form of a dict is received from the client.
2. A serializer (envelope type) defined in py:mod:`evalg.ballot_serializer`
   is then used to serialize and encrypt the ballot with the eleciton key.
3. The envelope type and serialized output is stored as an
   py:class:`Envelope` in the database.

The ``Envelope.id`` can later be used to commit the vote by using a
py:class:`evalg.models.votes.Vote` to bind the ballot to a voter.

"""
from typing import Dict
import uuid

from sqlalchemy.sql import schema
from sqlalchemy.sql import sqltypes

import evalg.database.types
from .base import ModelBase


class Envelope(ModelBase):

    __versioned__: Dict = {}
    __tablename__ = 'ballots'

    # a unique vote id - this is the ballot_id in the evalg.models.votes
    # models.
    id = schema.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        doc='a unique uuid for the ballot',
        primary_key=True,
    )

    # Describe how ballots are serialized.
    # E.g. base64-plaintext, base64-pkcs1
    envelope_type = schema.Column(
        sqltypes.UnicodeText,
        doc='a reference to the serializer/encryption used for this ballot',
        nullable=False,
    )

    # Ballot contents
    ballot_data = schema.Column(
        sqltypes.LargeBinary,
        doc='the ballot content',
    )
