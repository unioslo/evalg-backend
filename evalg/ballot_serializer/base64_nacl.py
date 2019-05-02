import json
import logging
import random
import string

from base64 import b64decode, b64encode
from nacl.encoding import Base64Encoder
from nacl.hash import blake2b
from nacl.public import Box, PublicKey, PrivateKey

from evalg.ballot_serializer.ballot_serializer import BallotSerializerBase


logge = logging.getLogger(__name__)

class Base64NaClSerializer(BallotSerializerBase):
    """

    """

    def __init__(self,
                 election_public_key=None,
                 election_private_key=None,
                 backend_public_key=None,
                 backend_private_key=None,
                 envelop_padded_len=None,
                 ):
        super().__init__()
        self._election_private_key = None
        self._election_public_key = None
        self._backend_private_key = None
        self._backend_public_key = None
        self.election_public_key = election_public_key
        self.election_private_key = election_private_key
        self.backend_public_key = backend_public_key
        self.backend_private_key = backend_private_key
        self._envelope_padded_len = envelop_padded_len

    def serialize(self, ballot):


        ballot = self._pad_ballot(ballot)

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
        """

        # Decrypt ballot and deserialize
        decrypted_ballot = self._decrypt(encrypted_ballot)
        deserialized_ballot = json.loads(self._decode(decrypted_ballot))

        ballot = self._remove_padding(deserialized_ballot)
        return ballot

    def generate_hash(self, ballot):
        """Generate a ballot hash.

        Ballot is unencrypted ballot_data.
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

    def _encode(self, ballot):
        """Encode """
        return b64encode(ballot.encode('utf-8'))

    def _decode(self, encoded_ballot):
        return b64decode(encoded_ballot).decode('utf-8')

    def _encrypt(self, data):
        """Encrypt the serialized ballot data."""

        if not self.election_public_key or not self.backend_private_key:
            raise ValueError('Can\' encrypt ballot. Election public key or '
                             'backend private key missing')

        encrypted_ballot = self._encryption_box.encrypt(
            data,
            encoder=Base64Encoder)

        # Return the string representation
        return encrypted_ballot

    def _decrypt(self, encrypted_data):
        """Decrypt serialized ballot_data."""
        if not self.election_private_key or not self.backend_public_key:
            raise ValueError('Can\' decrypt ballot. Election private key or '
                             'backend public key missing')

        decrypted_ballot = self._decryption_box.decrypt(
            encrypted_data,
            encoder=Base64Encoder)

        return decrypted_ballot

    def _pad_ballot(self, ballot):
        """Add padding to ballot."""

        ballot['padding'] = ''
        ballot_len = len(json.dumps(ballot))

        if ballot_len >= self._envelope_padded_len:
            logging.error('Found ballot that is bigger then the padded '
                          'total size. We can\'t hide the size of the ballot. '
                          'Increase ENVELOPE_PADDED_LEN to fix the problem.')
            pad_length = 0
        else:
            pad_length = self._envelope_padded_len - ballot_len

        ballot['padding'] = ''.join(
            random.choices(string.ascii_letters + string.digits,
                           k=pad_length))
        return ballot

    def _remove_padding(self, ballot):
        """Remove padding from ballot."""

        del ballot['padding']
        return ballot

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
        """Create or use existing key."""
        if not key:
            return None
        elif isinstance(key, key_class):
            return key
        else:
            return key_class(key, encoder=Base64Encoder)

    def _update_boxes(self):
        """Create and set the NaCl boxes."""
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
