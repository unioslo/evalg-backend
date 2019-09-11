"""
Database models for ballots.

This module defines a single object, py:class:`Envelope`, which is a simple
uuid -> binary data mapping.  Along with the binary data are some parameters on
how the binary data is encoded.

To leave a ballot, the process should be as follows:

1. A ballot is received from the client, and deserialized into a mapping/dict
   structure.
2. The ballot is mapped to a ballot format defined in (TODO)
   py:mod:`evalg.ballot`, based on which format the election type uses. An
   object is created based on the ballot dict.
3. A serializer (envelope type) defined in (TODO) py:mod:`evalg.ballot` is then
   used to serialize and encrypt the ballot with the eleciton key.
4. The ballot type, envelope type and serialized output is stored as an
   py:class:`Envelope` in the database.

The ``Envelope.id`` can later be used to commit the vote by using a
py:class:`evalg.models.votes.Vote` to bind the ballot to a voter.

"""
import uuid

from sqlalchemy.sql import schema
from sqlalchemy.sql import sqltypes

import evalg.database.types
from .base import ModelBase


class Envelope(ModelBase):

    __versioned__ = {}
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

    # Describe which ballot implementation (type and version) we're using.
    # E.g. stv:2, list:1
    ballot_type = schema.Column(
        sqltypes.UnicodeText,
        doc='a reference to the ballot object type used for this ballot',
        nullable=False,
    )

    # Ballot contents
    ballot_data = schema.Column(
        sqltypes.LargeBinary,
        doc='the ballot content',
    )
