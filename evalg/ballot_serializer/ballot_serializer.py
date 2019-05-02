"""
Ballot serializer/deserializer.

Abstract base of a ballot serializer/deserializer.
The serialized result must be a bytestring.
"""

from abc import ABC, abstractmethod


class BallotSerializerBase(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def serialize(self, ballot):
        """
        Serialize a ballot.

        :param ballot: A ballot.
        :return: The serialized ballot
        """
        pass

    @abstractmethod
    def deserialize(self, serialized_ballot):
        """
        Deserialize a ballot.

        :param serialized_ballot: A bytestring representation of a ballot.
        :return: The deserialized ballot
        """
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
