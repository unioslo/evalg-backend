import json

from base64 import b64decode, b64encode
from nacl.encoding import Base64Encoder
from nacl.hash import blake2b
from nacl.public import Box, PublicKey, PrivateKey

from evalg.ballot_serializer.ballot_serializer import BallotSerializerBase


class Base64NaClSerializer(BallotSerializerBase):
    """

    """

    def __init__(self,
                 election_public_key=None,
                 election_private_key=None,
                 backend_public_key=None,
                 backend_private_key=None):
        super().__init__()
        self._election_private_key = None
        self._election_public_key = None
        self._backend_private_key = None
        self._backend_public_key = None
        self.election_public_key = election_public_key
        self.election_private_key = election_private_key
        self.backend_public_key = backend_public_key
        self.backend_private_key = backend_private_key

    def serialize(self, ballot):

        # Dump the ballot object as json and encode it as a
        # base64 bytestring.
        serialized_ballot = self._encode(json.dumps(ballot))

        # Encrypt the serialised ballot
        encrypted_ballot = self._encrypt(serialized_ballot)

        return encrypted_ballot

    def deserialize(self, encrypted_ballot):
        """
        Deserialize and decrypts a ballot.


        Decryption:
        The elections private key and the backends public key is used to
        decrypt


        :param encrypted_ballot: A encrypted ballot
        :type encrypted_ballot: bytes
        :return: The decrypted ballot as a Ballot object
        :rtype: Ballot
        """

        # Decrypt ballot
        decrypted_ballot = self._decrypt(encrypted_ballot)

        # Deserialize into Ballot object
        deserialized_ballot = json.loads(self._decode(decrypted_ballot))
        return deserialized_ballot

    def generate_hash(self, ballot):
        """Generate a ballot hash.

        Ballot is the unencrypted ballot_data.
        """

        ballot_data = json.dumps(ballot, ensure_ascii=False).encode('utf-8')
        return blake2b(ballot_data, encoder=Base64Encoder)

    def is_valid_hash(self, hash, ballot):
        """Tests if a ballot hash is correct."""

        ballot_data = json.dumps(ballot, ensure_ascii=False).encode('utf-8')
        new_hash = blake2b(ballot_data, encoder=Base64Encoder)
        if hash != new_hash:
            return False
        return True

    def _encode(self, data):
        return b64encode(data.encode('utf-8'))

    def _decode(self, encoded_data):
        return b64decode(encoded_data).decode('utf-8')

    def _encrypt(self, data):
        """

        :param data: Serialized data
        :type data: bytes
        :return: Encrypted copy of the input data.
        :rtype: bytes
        """

        if not self.election_public_key or not self.backend_private_key:
            raise ValueError('Can\' encrypt ballot. Election public key or '
                             'backend private key missing')
        # TODO padding

        encrypted_ballot = self._encryption_box.encrypt(
            data,
            encoder=Base64Encoder)

        # Return the string representation
        return encrypted_ballot

    def _decrypt(self, encrypted_data):

        if not self.election_private_key or not self.backend_public_key:
            raise ValueError('Can\' decrypt ballot. Election private key or '
                             'backend public key missing')

        decrypted_ballot = self._decryption_box.decrypt(
            encrypted_data,
            encoder=Base64Encoder)

        return decrypted_ballot

    def _create_padding(self):
        pass

    @property
    def envelope_type(self):
        return 'base64-nacl'

    @property
    def election_public_key(self):
        return self._election_public_key

    @election_public_key.setter
    def election_public_key(self, key):
        self._election_public_key = self._create_key_instance(key, PublicKey)
        self._update_boxes()

    @property
    def election_private_key(self):
        return self._election_private_key

    @election_private_key.setter
    def election_private_key(self, key):
        self._election_private_key = self._create_key_instance(key, PrivateKey)
        self._update_boxes()

    @property
    def backend_public_key(self):
        return self._backend_public_key

    @backend_public_key.setter
    def backend_public_key(self, key):
        self._backend_public_key = self._create_key_instance(key, PublicKey)
        self._update_boxes()

    @property
    def backend_private_key(self):
        return self._backend_private_key

    @backend_private_key.setter
    def backend_private_key(self, key):
        self._backend_private_key = self._create_key_instance(key, PrivateKey)
        self._update_boxes()

    def _create_key_instance(self, key, key_class):
        if not key:
            return None
        elif isinstance(key, key_class):
            return key
        else:
            return key_class(key, encoder=Base64Encoder)

    def _update_boxes(self):

        if self.election_private_key and self.backend_public_key:
            self._decryption_box = Box(
                self.election_private_key,
                self.backend_public_key)
        else:
            self._decryption_box = None

        if self.election_public_key and self.backend_private_key:
            self._encryption_box = Box(
                self.backend_private_key,
                self.election_public_key)
        else:
            self._encryption_box = None