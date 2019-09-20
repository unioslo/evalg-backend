"""Provides tests for the private key backup functionality"""

import nacl.encoding
import nacl.public


def test_master_key_generation(make_master_key):
    """Tests the generation of master keys"""
    privkey, master_key = make_master_key()
    assert privkey.public_key
    pubkey = privkey.public_key.encode(nacl.encoding.Base64Encoder)
    assert master_key
    assert pubkey == master_key.public_key
