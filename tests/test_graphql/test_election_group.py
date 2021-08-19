"""Test election group related graphql queries and mutation."""
import pytest

from evalg.models.election import ElectionGroup
from evalg.graphql import get_context

# TODO, move all election group test here


@pytest.mark.parametrize(
    'template_name, expected_election_nr, election_type, name',
    [('uio_principal', 1, 'single_election', None),
     ('uio_dean', 1, 'single_election', None),
     ('uio_department_leader', 1, 'single_election', None),
     ('uio_university_board', 4, 'multiple_elections', None),
     ('uio_faculty_board', 4, 'multiple_elections', None),
     ('uio_department_board', 4, 'multiple_elections', None),
     ('uio_student_parliament', 1, 'single_election', None),
     ('uio_vb_lamu', 1, 'multiple_elections', {
         'en': 'en',
         'nb': 'nb',
         'nn': 'nn'
     }),
     ]
)
def test_create_election_group_mutation(
        template_name,
        expected_election_nr,
        election_type,
        name,
        client,
        ou_generator,
        logged_in_user):
    """Test the CreateNewElectionGroup mutation."""
    ou = ou_generator()
    variables = {
        'ouId': str(ou.id),
        'template': True,
        'templateName': template_name,
        'name': name
    }
    mutation = """
    mutation ($ouId: UUID!,
              $template: Boolean!,
              $templateName: String!,
              $name: ElectionName) {
        createNewElectionGroup(ouId: $ouId,
                               template: $template,
                               templateName: $templateName,
                               nameDict: $name) {
            ok
            electionGroup {
                id
                announced
                elections {
                    id
                    active
                }
                name
                ouId
                publicKey
                published
                type
            }
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['createNewElectionGroup']
    assert response['ok']

    election_group = response['electionGroup']

    assert not election_group['announced']
    assert not election_group['published']
    assert election_group['ouId'] == str(ou.id)
    assert election_group['publicKey'] is None
    assert election_group['type'] == election_type

    assert len(election_group['elections']) == expected_election_nr
    for election in election_group['elections']:
        if election_type == 'single_election':
            assert election['active']

    election_group_db = ElectionGroup.query.get(election_group['id'])
    assert election_group_db
    assert not election_group_db.announced
    assert election_group_db.ou_id == ou.id
    assert not election_group_db.published

    if name:
        assert name == election_group['name']


@pytest.mark.parametrize(
    'key, success',
    [
        # Valid base64 key
        ('bO1pw6/Bslji0XvXveSuVbe4vp93K1DcpqYgIxRhYAs=', True),
        # Base64 key with none ascii character
        ('bO1pw6/Bslji0XvXveæuVbe4vp93K1DcpqYgIxRhYAs=', False),
        # Base64 key missing one character
        ('bO1pw6/BsljiXvXveSuVbe4vp93K1DcpqYgIxRhYAs=', False),
        # Empty string
        ('', False),
        # None base64 string
        ('æøå', False),
    ]
)
def test_set_election_group_key_mutation(
        key,
        success,
        client,
        election_group_generator):
    """Test the SetElectionGroupKey mutation."""
    election_group = election_group_generator(owner=True)
    variables = {
        'id': str(election_group.id),
        'publicKey': key
    }
    mutation = """
    mutation ($id: UUID!, $publicKey: String!) {
        setElectionGroupKey(id: $id, publicKey: $publicKey) {
            success
            code
            message
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['setElectionGroupKey']

    assert response['success'] == success
    election_group_db = ElectionGroup.query.get(election_group.id)
    assert (election_group_db.public_key == key) == success


# def test_update_election_group_name_mutation(
#         name,
#         client,
#         make_election_group_from_template,
#         logger_in_user):
#     """Test the UpdateElectionGroupName mutation"""
#     election_group = make_election_group(
#         'set_key_test', 'uio_dean', logged_in_user)
