"""Tests queries and mutations for the private key backup functionality"""
import nacl.encoding

from evalg.graphql import get_context


def test_query_master_keys(client, make_master_key):
    """Tests the master_keys query"""
    privkey, master_key = make_master_key()
    query = """
    query masterKeys {
        masterKeys {
            id
            publicKey
            description
            active
        }
    }
    """
    execution = client.execute(
        query, variables={}, context=get_context())
    assert master_key.public_key
    assert not execution.get('errors')
    assert len(execution['data']['masterKeys']) == 1
    master_key_data = execution['data']['masterKeys'][0]
    assert master_key_data['publicKey'] == master_key.public_key
    assert (privkey.public_key.encode(nacl.encoding.Base64Encoder).decode() ==
            master_key_data['publicKey'])
    assert master_key_data['description'] == 'Master key for testing'
    assert master_key_data['active'] is True
    # change / remove the next case in case of new and different key-length
    assert master_key.public_key[-1] == '='
