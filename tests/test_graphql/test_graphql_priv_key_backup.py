"""Tests queries and mutations for the private key backup functionality"""
import nacl.encoding
import nacl.public

from evalg.graphql import get_context
from evalg.models.privkeys_backup import ElectionGroupKeyBackup


def test_query_master_keys(client, db_session, master_key):
    """Tests the master_keys query"""
    privkey, master_key = master_key(db_session)
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


def test_mutation_add_election_group_key_backup(client,
                                                db_session,
                                                make_election_group,
                                                master_key):
    """Tests the add_election_group_key_backup mutation"""
    privkey, master_key = master_key(db_session)
    election_group = make_election_group('add_election_group_key_backup test',
                                         admin=True)
    mutation = """
    mutation (
        $electionGroupId: UUID!
        $encryptedPrivKey: String!
        $masterKeyId: UUID!
    ) {
        addElectionGroupKeyBackup(
            electionGroupId: $electionGroupId
            encryptedPrivKey: $encryptedPrivKey
            masterKeyId: $masterKeyId
        ) {
            success
        }
    }
    """
    # could put any str, but let's do things properly...
    new_priv_key = nacl.public.PrivateKey.generate()
    message = 'privkey: '.encode() + new_priv_key.encode(
        encoder=nacl.encoding.Base64Encoder)
    ebox = nacl.public.Box(new_priv_key, privkey.public_key)
    encrypted_priv_key = ebox.encrypt(message,
                                      encoder=nacl.encoding.Base64Encoder)
    execution = client.execute(
        mutation,
        variables={'electionGroupId': str(election_group.id),
                   'encryptedPrivKey': encrypted_priv_key.decode(),
                   'masterKeyId': str(master_key.id)},
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupKeyBackup']
    assert response['success']
    key_backups = ElectionGroupKeyBackup.query.filter_by(
        election_group_id=election_group.id,
        master_key_id=master_key.id,
        active=True).all()
    assert len(key_backups) == 1
    assert isinstance(key_backups[0].encrypted_priv_key, str)
    dbox = nacl.public.Box(privkey, new_priv_key.public_key)
    assert (dbox.decrypt(key_backups[0].encrypted_priv_key,
                         encoder=nacl.encoding.Base64Encoder) ==
            message)
    # now create a new key and see if the previous backup will be invalidated
    new_priv_key = nacl.public.PrivateKey.generate()
    message = 'privkey: '.encode() + new_priv_key.encode(
        encoder=nacl.encoding.Base64Encoder)
    ebox = nacl.public.Box(new_priv_key, privkey.public_key)
    encrypted_priv_key = ebox.encrypt(message,
                                      encoder=nacl.encoding.Base64Encoder)
    execution = client.execute(
        mutation,
        variables={'electionGroupId': str(election_group.id),
                   'encryptedPrivKey': encrypted_priv_key.decode(),
                   'masterKeyId': str(master_key.id)},
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupKeyBackup']
    assert response['success']
    key_backups = ElectionGroupKeyBackup.query.filter_by(
        election_group_id=election_group.id,
        master_key_id=master_key.id)
    # 2 backups and only 1 active
    assert key_backups.count() == 2
    assert key_backups.filter_by(active=True).count() == 1
