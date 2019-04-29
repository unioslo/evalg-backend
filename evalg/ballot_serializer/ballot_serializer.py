"""Ballot serializer/deserializer."""

import json

from abc import ABC, abstractmethod
from base64 import b64decode, b64encode

from nacl.encoding import Base64Encoder
from nacl.public import Box, PublicKey, PrivateKey

class BallotSerializerBase(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def serialize(self, ballot):
        pass

    @abstractmethod
    def deserialize(self, encrypted_ballot):
        pass

    @abstractmethod
    def generate_hash(self, ballot):
        pass

    @abstractmethod
    def is_valid_hash(self, hash, ballot):
        pass

    @property
    @abstractmethod
    def envelope_type(self):
        pass



