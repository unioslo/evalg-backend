"""Tests for the base64-nacl serializer."""
import pytest

from nacl.exceptions import CryptoError
from nacl.public import PublicKey, PrivateKey
from nacl.utils import EncryptedMessage


def test_base64_nacl_encoding(ballot_serializer):
    """Test correct encoding and decoding."""

    data = "Test 123 øæå £$@đðþß"
    encoded = ballot_serializer._encode(data)
    decoded = ballot_serializer._decode(encoded)

    assert encoded
    assert decoded
    assert isinstance(encoded, bytes)
    assert encoded != decoded
    assert decoded == data


def test_base64_nacl_encryption(ballot_serializer):

    data = b'Test 123'
    encrypted_data = ballot_serializer._encrypt(data)
    decrypted_data = ballot_serializer._decrypt(encrypted_data)

    assert isinstance(data, bytes)
    assert encrypted_data
    assert decrypted_data
    assert isinstance(encrypted_data, bytes)
    assert decrypted_data == data



def test_base64_nacl_keys(ballot_serializer):
    """Tests that the key objects are created correctly."""
    assert isinstance(ballot_serializer.backend_private_key, PrivateKey)
    assert isinstance(ballot_serializer.backend_public_key, PublicKey)
    assert isinstance(ballot_serializer.election_private_key, PrivateKey)
    assert isinstance(ballot_serializer.election_public_key, PublicKey)


def test_base64_nacl_serializer(ballot_serializer, ballot):

    ballot_serialized = ballot_serializer.serialize(ballot)
    assert ballot_serialized
    assert ballot_serialized != ballot
    assert isinstance(ballot_serialized, EncryptedMessage)
    assert ballot_serialized.ciphertext
    assert ballot_serialized.nonce

    # Convert to bytes to simulate storing the ballot in the database
    ballot_serialized = bytes(ballot_serialized)

    # Decrypt and deserializ into dict
    ballot_deserialized = ballot_serializer.deserialize(ballot_serialized)
    assert ballot_deserialized
    assert isinstance(ballot_deserialized, dict)
    assert ballot_deserialized == ballot


def test_base64_nacl_wrong_election_private_key(ballot_serializer, ballot):
    """Try deserializing with the wrong election private key."""
    ballot_serializer.election_private_key = \
        "errorvWaLgFBEwpjxzQBxgaRlEprD0AlVHKw+3ImTnc="
    serialized_ballot = ballot_serializer.serialize(ballot)

    assert serialized_ballot

    with pytest.raises(CryptoError):
        ballot_serializer.deserialize(serialized_ballot)


def test_base64_nacl_wrong_backend_public_key(ballot_serializer, ballot):
    """Try deserializing with the wrong backend public key."""
    ballot_serializer.backend_public_key = \
        "errorvWaLgFBEwpjxzQBxgaRlEprD0AlVHKw+3ImTnc="
    serialized_ballot = ballot_serializer.serialize(ballot)
    assert serialized_ballot
    with pytest.raises(CryptoError):
        ballot_serializer.deserialize(serialized_ballot)


def test_base64_nacl_corrupt_data(ballot_serializer, ballot):
    """Try deserializing corrupt data."""
    serialized_ballot = ballot_serializer.serialize(ballot)
    assert serialized_ballot
    tmp = bytearray(serialized_ballot)
    tmp[-10] = 65 if tmp[-10] != 65 else 66
    corrupt_ballot = EncryptedMessage(tmp)
    with pytest.raises(CryptoError):
        ballot_serializer.deserialize(corrupt_ballot)
